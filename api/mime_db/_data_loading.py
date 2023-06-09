import json
import logging
from pathlib import Path
from typing import Callable
from uuid import UUID

import numpy as np


async def add_video(self, video_name: str, video_metadata: dict) -> UUID:
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

    if not isinstance(video_id, UUID):
        raise ValueError(f"Unable to add video '{video_name}'")

    return video_id


async def clear_poses(self, video_id: UUID) -> None:
    await self._pool.execute("DELETE FROM pose WHERE video_id = $1;", video_id)


async def load_openpifpaf_predictions(
    self, video_id: UUID, json_path: Path, clear=True
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
    video_id: UUID | None,
    annotation_func: Callable,
    reindex=True,
) -> None:
    async with self._pool.acquire() as conn:
        await conn.execute(
            f"ALTER TABLE pose ADD COLUMN IF NOT EXISTS {column} {col_type};"
        )

        poses = await conn.fetch("SELECT * FROM pose WHERE video_id = $1;", video_id)
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
