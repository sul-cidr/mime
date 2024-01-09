import copy
import json
import logging
from pathlib import Path
from typing import Callable
from uuid import UUID

import joblib
import numpy as np

phalp_to_coco = [[0], [16], [15], [18], [17], [5, 34], [2, 33], [6, 35], [3, 32], [7, 36], [4, 31], [28], [27], [13, 29], [10, 26], [14, 30], [11, 25]]

def merge_phalp_coords(all_coords, phalp_to_merge):
    new_coords = []
    for to_merge in phalp_to_merge:
        x_avg = sum([all_coords[i][0] for i in to_merge]) / len(to_merge)
        y_avg = sum([all_coords[i][1] for i in to_merge]) / len(to_merge)
        new_coords.append([x_avg, y_avg, 1.0]) # Add a bogus confidence value because the other code expects it
        
    return np.array(new_coords)


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


async def clear_4dh_poses(self, video_id: UUID) -> None:
    await self._pool.execute("DELETE FROM pose4dh WHERE video_id = $1;", video_id)


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


async def load_4dh_predictions(
    self, video_id: UUID, pkl_path: Path, clear=True
) -> None:
    frames = {}

    if clear:
        logging.debug(f"Clearing poses for video {video_id}")
        await self.clear_4dh_poses(video_id)

    logging.info(f"Importing data from '{pkl_path}'...")

    frames = joblib.load(pkl_path)

    logging.info(f"Loading data for {len(frames)} frames from '{pkl_path}'...")

    poses = []
    for frame_path, frame in frames.items():

        if not len(frame["2d_joints"]):
            continue

        for pose_idx, pose in enumerate(frame["2d_joints"]):

            img_height, img_width = frame["size"][pose_idx]
            img_size = max(img_width, img_height)
            joints_2d = copy.deepcopy(pose)
            joints_2d = joints_2d.reshape(-1, 2)
            joints_2d *= img_size
            joints_2d[:,1] -= (max(img_width, img_height) - min(img_width, img_height)) / 2

            coco_joints = merge_phalp_coords(joints_2d, phalp_to_coco).flatten()

            poses.append(
                {
                    "video_id": video_id,
                    "frame": frame["time"],
                    "pose_idx": pose_idx,
                    #"keypoints": joints_2d.flatten(),
                    "keypoints": coco_joints,
                    "bbox": np.array(frame["bbox"][pose_idx]),
                    "score": frame["conf"][pose_idx],
                    "category": frame["class_name"][pose_idx],
                    "track_id": frame["tid"][pose_idx],
                }
            )

    data = [tuple(pose.values()) for pose in poses]

    await self._pool.executemany(
        """
        INSERT INTO pose (
            video_id, frame, pose_idx, keypoints, bbox, score, category, track_id)
            VALUES($1, $2, $3, $4, $5, $6, $7, $8)
        ;
        """,
        data,
    )

    logging.info(f"Loaded {len(poses)} predictions!")


async def add_shot_boundaries(self, video_id: UUID | None, frames_data) -> None:
    data = [(video_id,) + tuple(face) for face in frames_data]

    await self._pool.executemany(
        """
        INSERT INTO frame (
            video_id, frame, local_shot_prob, global_shot_prob, is_shot_boundary)
            VALUES($1, $2, $3, $4, $5)
        ;
        """,
        data,
    )


async def add_frame_movement(
    self, video_id: UUID | None, max_movement, movement_data
) -> None:
    async with self._pool.acquire() as conn:
        await conn.execute(
            """
            ALTER TABLE frame ADD COLUMN IF NOT EXISTS total_movement FLOAT DEFAULT 0.0
            ;
            """
        )

        safe_max = max(1, max_movement)  # Just in case a 0 sneaks in...

        for frame in movement_data:
            await conn.execute(
                """
                UPDATE frame
                SET total_movement = $1
                WHERE video_id = $2 AND frame = $3
                ;
                """,
                movement_data[frame] / safe_max,
                video_id,
                frame,
            )


async def add_video_tracks(self, video_id: UUID | None, track_data) -> None:
    async with self._pool.acquire() as conn:
        await conn.execute(
            """
            ALTER TABLE pose ADD COLUMN IF NOT EXISTS track_id INTEGER DEFAULT NULL
            ;
            """
        )

        for track in track_data:
            await conn.execute(
                """
                UPDATE pose
                SET track_id = $1
                WHERE video_id = $2 AND frame = $3 AND pose_idx = $4
                ;
                """,
                track["track_id"],
                video_id,
                track["frame"],
                track["pose_idx"],
            )


async def add_video_faces(self, video_id: UUID | None, faces_data) -> None:
    data = [(video_id,) + tuple(face) for face in faces_data]

    await self._pool.executemany(
        """
        INSERT INTO face (
            video_id, frame, bbox, confidence, landmarks, embedding)
            VALUES($1, $2, $3, $4, $5, $6)
        ;
        """,
        data,
    )

    logging.info(f"Loaded {len(faces_data)} faces!")


async def add_pose_faces(self, faces_data) -> None:
    data = [tuple(face) for face in faces_data]

    async with self._pool.acquire() as conn:
        await conn.execute(
            """
            ALTER TABLE face ADD COLUMN IF NOT EXISTS track_id INTEGER DEFAULT NULL
            ;
            """
        )

        await conn.executemany(
            """
            INSERT INTO face (
                video_id, frame, pose_idx, bbox, confidence, landmarks, embedding, track_id)
                VALUES($1, $2, $3, $4, $5, $6, $7, $8)
            ;
            """,
            data,
        )

    logging.info(f"Loaded {len(faces_data)} matched faces!")


async def add_video_movelets(self, movelets_data, reindex=True) -> None:
    data = [tuple(movelet) for movelet in movelets_data]
    await self._pool.executemany(
        """
        INSERT INTO movelet (
            video_id,
            track_id,
            tick,
            start_frame,
            end_frame,
            pose_idx,
            start_timecode,
            end_timecode,
            prev_norm,
            norm,
            motion,
            movement)
            VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ;
        """,
        data,
    )

    logging.info(f"Loaded {len(movelets_data)} movelets!")

    if reindex:
        logging.info("Creating approximate distance index for movelets...")
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                CREATE INDEX ON movelet
                USING ivfflat (motion vector_cosine_ops)
                ;
                """,
            )


async def assign_face_clusters(self, video_id, cluster_id, faces_data) -> None:
    async with self._pool.acquire() as conn:
        await conn.execute(
            "ALTER TABLE face ADD COLUMN IF NOT EXISTS cluster_id INTEGER DEFAULT NULL;"
        )
        async with conn.transaction():
            for pose_face in faces_data:
                await conn.execute(
                    """
                        UPDATE face
                        SET cluster_id = $1
                        WHERE video_id = $2 AND frame = $3 AND pose_idx = $4
                        ;
                    """,
                    cluster_id,
                    video_id,
                    pose_face["frame"],
                    pose_face["pose_idx"],
                )


async def assign_face_clusters_by_track(self, video_id, cluster_id, track_id) -> None:
    async with self._pool.acquire() as conn:
        await conn.execute(
            "ALTER TABLE face ADD COLUMN IF NOT EXISTS cluster_id INTEGER DEFAULT NULL;"
        )
        await conn.execute(
            """
                UPDATE face
                SET cluster_id = $1
                WHERE video_id = $2 AND track_id = $3
                ;
            """,
            cluster_id,
            video_id,
            track_id,
        )


async def assign_movelet_clusters(self, movelet_clusters) -> None:
    async with self._pool.acquire() as conn:
        await conn.execute(
            """
            ALTER TABLE movelet
                ADD COLUMN IF NOT EXISTS cluster_id INTEGER DEFAULT NULL;
            """
        )

        # updates = [(account_id, new_address, additional_protocol) from <data_source>]

        await conn.executemany(
            """
            UPDATE movelet
            SET cluster_id = $5
            WHERE video_id = $1 AND
                  pose_idx = $2 AND
                  start_frame = $3 AND
                  end_frame = $4;
            """,
            movelet_clusters,
        )

        return


async def annotate_pose(
    self,
    column: str,
    col_type: str,
    video_id: UUID | None,
    annotation_func: Callable,
    reindex=True,
    pose_tbl = "pose",
) -> None:
    async with self._pool.acquire() as conn:
        await conn.execute(
            f"ALTER TABLE {pose_tbl} ADD COLUMN IF NOT EXISTS {column} {col_type};"
        )

        poses = await conn.fetch(f"SELECT * FROM {pose_tbl} WHERE video_id = $1;", video_id)
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
                    UPDATE {pose_tbl}
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
                CREATE INDEX ON {pose_tbl}
                USING ivfflat ({column} vector_cosine_ops)
                ;
                """,
            )
    return


async def annotate_movelet(
    self,
    column: str,
    col_type: str,
    video_id: UUID | None,
    annotation_func: Callable,
    reindex=True,
) -> None:
    async with self._pool.acquire() as conn:
        await conn.execute(
            f"ALTER TABLE movelet ADD COLUMN IF NOT EXISTS {column} {col_type};"
        )

        movelets = await conn.fetch(
            "SELECT * FROM movelets WHERE video_id = $1;", video_id
        )
        async with conn.transaction():
            for i, movelet in enumerate(movelets):
                if i % (len(movelets) // 10) == 0:
                    logging.info(
                        f"Annotating movelet {i:7}/{len(movelets)} "
                        f"({10 * (i // (len(movelets) // 10)):3}%)..."
                    )
                annotation_value = annotation_func(movelet)
                await conn.execute(
                    f"""
                    UPDATE movelet
                    SET {column} = $1
                    WHERE video_id = $2 AND tick = $3 AND track_id = $4
                    ;
                    """,
                    annotation_value,
                    video_id,
                    movelet["tick"],
                    movelet["track_id"],
                )

        if reindex:
            logging.info("Creating approximate index for cosine distance...")
            await conn.execute(
                f"""
                CREATE INDEX ON movelet
                USING ivfflat ({column} vector_cosine_ops)
                ;
                """,
            )
    return
