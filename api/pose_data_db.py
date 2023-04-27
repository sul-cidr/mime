"""PoseDataDatabase class to abstract out the database interaction."""

import itertools
import json
import logging
import os
from operator import itemgetter
from pathlib import Path
from statistics import mean
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

    pool: asyncpg.Pool

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    @classmethod
    async def create(cls, drop=False) -> "PoseDataDatabase":
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
        await register_vector(conn)

    @staticmethod
    async def initialize_db(conn, drop=False) -> None:
        if drop:
            logging.warn("Dropping database tables...")
            await conn.execute("DROP TABLE IF EXISTS video CASCADE;")
            await conn.execute("DROP TABLE IF EXISTS pose CASCADE;")

        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")

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
        video_id = await self.pool.fetchval(
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
        await self.pool.execute("DELETE FROM pose WHERE video_id = $1;", video_id)

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

        await self.pool.executemany(
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
        await self.pool.execute(
            f"ALTER TABLE pose ADD COLUMN IF NOT EXISTS {column} {col_type};"
        )

        poses = await self.pool.fetch(
            "SELECT * FROM pose WHERE video_id = $1;", video_id
        )
        async with self.pool.transaction():
            for i, pose in enumerate(poses):
                if i % (len(poses) // 10) == 0:
                    logging.info(
                        f"Annotating pose {i:7}/{len(poses)} "
                        f"({10 * (i // (len(poses) // 10)):3}%)..."
                    )
                annotation_value = annotation_func(pose)
                await self.pool.execute(
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
            await self.pool.execute(
                f"""
                CREATE INDEX ON pose
                  USING ivfflat ({column} vector_cosine_ops)
                ;
                """,
            )
        return

    async def get_available_videos(self) -> list:
        videos = await self.pool.fetch("SELECT * FROM video;")
        return videos

    async def get_video_by_id(self, video_id: int) -> asyncpg.Record:
        return await self.pool.fetchrow("SELECT * FROM video WHERE id = $1;", video_id)

    async def get_pose_data_by_frame(self, video_id: int) -> list:
        pose_data = await self.pool.fetch(
            "SELECT * FROM pose WHERE video_id = $1;", video_id
        )
        pose_data.sort(key=itemgetter("frame"))

        by_frame = {
            frame: list(poses)
            for frame, poses in itertools.groupby(pose_data, itemgetter("frame"))
        }

        return [
            {
                "frame": frame,
                "poseCt": len(by_frame.get(frame, [])),
                "avgScore": 0
                if frame not in by_frame
                else mean(_["score"] for _ in by_frame[frame]),
            }
            for frame in range(len(by_frame))
        ]

    async def get_pose_annotations(self, column: str, video_id: int) -> list[np.ndarray]:
        annotations = await self.pool.fetch(
            f"SELECT {column} FROM pose WHERE video_id = $1;", video_id
        )
        return [np.array(_[column]) for _ in annotations]

    async def get_frame_data(self, video_id: int, frame: int) -> list:
        return await self.pool.fetch(
            "SELECT * FROM pose WHERE video_id = $1 AND frame = $2;", video_id, frame
        )
