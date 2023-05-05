"""PoseDataDatabase class to abstract out the database interaction."""

import json
import logging
import os
from pathlib import Path
from typing import Callable

import asyncpg
import numpy as np
from dotenv import load_dotenv
from pgvector.asyncpg import register_vector

logging.getLogger("dotenv.main").setLevel(logging.FATAL)

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

try:
    assert all((DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT))
except AssertionError:
    raise SystemExit(
        "Error: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT are all required"
    ) from None


class PoseDataDatabase:
    """Class to interact with the database."""

    _pool: asyncpg.Pool

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @classmethod
    async def create(cls, drop=False) -> "PoseDataDatabase":
        """Factory method to create a new PoseDataDatabase instance.
        Required because __init__ doesn't work well with async/await.
        """
        pool = await PoseDataDatabase.get_pool()

        async with pool.acquire() as conn:
            await PoseDataDatabase.initialize_db(conn, drop)

        return cls(pool)

    @staticmethod
    async def get_pool() -> asyncpg.Pool:
        pool = await asyncpg.create_pool(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            port=DB_PORT,
            setup=PoseDataDatabase.setup_connection,
        )
        if not pool:
            raise RuntimeError("Database connection could not be established")
        return pool

    @staticmethod
    async def get_connection() -> asyncpg.Connection:
        conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            port=DB_PORT,
        )
        await PoseDataDatabase.setup_connection(conn)
        return conn

    @staticmethod
    async def setup_connection(conn: asyncpg.Connection):
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        await register_vector(conn)

    @staticmethod
    async def initialize_db(conn, drop=False) -> None:
        if drop:
            logging.warn("Dropping database tables...")
            await conn.execute("DROP TABLE IF EXISTS video CASCADE;")
            await conn.execute("DROP TABLE IF EXISTS pose CASCADE;")

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS video (
                id serial PRIMARY KEY,
                video_name VARCHAR(150) UNIQUE NOT NULL,
                frame_count INTEGER NOT NULL,
                fps FLOAT NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                created_on TIMESTAMP NOT NULL DEFAULT NOW()
            )
            ;
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pose (
                video_id INTEGER NOT NULL REFERENCES video(id) ON DELETE CASCADE,
                frame INTEGER NOT NULL,
                pose_idx INTEGER NOT NULL,
                keypoints vector(51) NOT NULL,
                bbox FLOAT[4] NOT NULL,
                score FLOAT NOT NULL,
                category INTEGER,
                PRIMARY KEY(video_id, frame, pose_idx)
            )
            ;
            """
        )

    async def add_video(self, video_name: str, video_metadata: dict) -> int:
        video_id = await self._pool.fetchval(
            """
            INSERT
              INTO video (video_name, frame_count, fps, width, height)
              VALUES($1, $2, $3, $4, $5)
              ON CONFLICT (video_name) DO UPDATE
                SET frame_count = $2, fps = $3, width = $4, height = $5
              RETURNING id
            ;
            """,
            video_name,
            *video_metadata.values(),
        )
        logging.debug(f"'{video_name}' has ID {video_id}")

        if not isinstance(video_id, int):
            raise ValueError(f"Unable to add video '{video_name}'")

        return video_id

    async def clear_poses(self, video_id: int) -> None:
        await self._pool.execute("DELETE FROM pose WHERE video_id = $1;", video_id)

    async def load_openpifpaf_predictions(
        self, video_id: int, json_path: Path, clear=True
    ) -> None:
        frames = []
        with json_path.open("r", encoding="utf8") as _fh:
            for line in _fh:
                frames.append(json.loads(line))

        if clear:
            logging.debug(f"Clearing poses for video {video_id}")
            await self.clear_poses(video_id)

        logging.info(f"Loading data for {len(frames)} frames from '{json_path}'...")

        poses = []
        for frame in frames:
            assert frame.keys() == {"frame", "predictions"}

            if not len(frame["predictions"]):
                continue

            for pose_id, pose in enumerate(frame["predictions"]):
                poses.append(
                    {
                        "video_id": video_id,
                        "frame": frame["frame"],
                        "pose_id": pose_id,
                        "keypoints": np.array(pose["keypoints"]),
                        "bbox": np.array(pose["bbox"]),
                        "score": pose["score"],
                        "category": pose["category_id"],
                    }
                )

        data = [tuple(pose.values()) for pose in poses]

        await self._pool.executemany(
            """
            INSERT INTO pose (
              video_id, frame, pose_idx, keypoints, bbox, score, category)
              VALUES($1, $2, $3, $4, $5, $6, $7)
            ;
            """,
            data,
        )

        logging.info(f"Loaded {len(poses)} predictions!")

    async def annotate_pose(
        self,
        column: str,
        col_type: str,
        video_id: int | None,
        annotation_func: Callable,
        reindex=True,
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"ALTER TABLE pose ADD COLUMN IF NOT EXISTS {column} {col_type};"
            )

            poses = await conn.fetch(
                "SELECT * FROM pose WHERE video_id = $1;", video_id
            )
            async with conn.transaction():
                for i, pose in enumerate(poses):
                    if i % (len(poses) // 10) == 0:
                        logging.info(
                            f"Annotating pose {i:7}/{len(poses)} "
                            f"({10 * (i // (len(poses) // 10)):3}%)..."
                        )
                    annotation_value = annotation_func(pose)
                    await conn.execute(
                        f"""
                        UPDATE pose
                        SET {column} = $1
                        WHERE video_id = $2 AND frame = $3 AND pose_idx = $4
                        ;
                        """,
                        annotation_value,
                        video_id,
                        pose["frame"],
                        pose["pose_idx"],
                    )

            if reindex:
                logging.info("Creating approximate index for cosine distance...")
                await conn.execute(
                    f"""
                    CREATE INDEX ON pose
                    USING ivfflat ({column} vector_cosine_ops)
                    ;
                    """,
                )
        return

    async def get_available_videos(self) -> list:
        videos = await self._pool.fetch("SELECT * FROM video;")
        return videos

    async def get_video_by_id(self, video_id: int) -> asyncpg.Record:
        return await self._pool.fetchrow("SELECT * FROM video WHERE id = $1;", video_id)

    async def get_pose_data_by_frame(self, video_id: int) -> list:
        return await self._pool.fetch(
            """
            SELECT frame,
                   count(pose_idx) AS "poseCt",
                   ROUND(AVG(score)::numeric, 2) AS "avgScore"
            FROM pose
            WHERE video_id = $1
            GROUP BY frame
            ORDER BY frame;
            """,
            video_id,
        )

    async def get_pose_annotations(
        self, column: str, video_id: int
    ) -> list[np.ndarray]:
        annotations = await self._pool.fetch(
            f"SELECT {column} FROM pose WHERE video_id = $1;", video_id
        )
        return [np.array(_[column]) for _ in annotations]

    async def get_frame_data(self, video_id: int, frame: int) -> list:
        return await self._pool.fetch(
            "SELECT * FROM pose WHERE video_id = $1 AND frame = $2;", video_id, frame
        )

    async def get_nearest_neighbors(
        self, video_id: int, frame: int, pose_idx: int, metric="cosine", limit=5
    ) -> list:
        sub_query = """
            SELECT norm
            FROM pose
            WHERE video_id = $1 AND frame = $2 AND pose_idx = $3
            """

        distance = {
            "cosine": f"norm <=> ({sub_query})",
            "euclidean": f"norm <-> ({sub_query})",
            "innerproduct": f"norm <#> ({sub_query})",
        }[metric]

        return await self._pool.fetch(
            f"""
            SELECT *, {distance} AS distance FROM pose
            WHERE video_id = $1 AND NOT (frame = $2 AND pose_idx = $3)
            ORDER BY distance
            LIMIT $4;
            """,
            video_id,
            frame,
            pose_idx,
            limit,
        )
