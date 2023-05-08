import asyncpg
import numpy as np


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


async def get_pose_annotations(self, column: str, video_id: int) -> list[np.ndarray]:
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
