import copy
import json
import logging
from pathlib import Path
from typing import Callable
from uuid import UUID

import joblib
import numpy as np

# This reduces the 45 PHALP coords to 26, just by merging pairs that are very
# close together (e.g., left elbow front and left elbow back)
phalp_to_reduced = [
    [0, 15, 16, 17, 18, 38, 43],
    [1, 37, 40],
    [2, 33],
    [3, 32],
    [4, 31],
    [5, 34],
    [6, 35],
    [7, 36],
    [8, 39],
    [9],
    [10, 26],
    [11, 24],
    [12],
    [13, 29],
    [14, 21],
    [19, 20],
    [21],
    [22, 23],
    [25],
    [27],
    [28],
    [30],
    [36],
    [41],
    [42],
    [44],
]

phalp_to_coco_17 = [
    [0],
    [16],
    [15],
    [18],
    [17],
    [5, 34],
    [2, 33],
    [6, 35],
    [3, 32],
    [7, 36],
    [4, 31],
    [28],
    [27],
    [13, 29],
    [10, 26],
    [14, 30],
    [11, 25],
]

phalp_to_coco_13 = [
    [0],
    [5, 34],
    [2, 33],
    [6, 35],
    [3, 32],
    [7, 36],
    [4, 31],
    [28],
    [27],
    [13, 29],
    [10, 26],
    [14, 30],
    [11, 25],
]

openpifpaf_to_coco_13 = [
    [0],
    [5],
    [6],
    [7],
    [8],
    [9],
    [10],
    [11],
    [12],
    [13],
    [14],
    [15],
    [16],
]

CONF_THRESH_4DH = 0.85  # This is .8 in the PHALP software


def merge_coords(all_coords, guide_to_merge, has_confidence=False):
    new_coords = []
    for to_merge in guide_to_merge:
        x_avg = sum([all_coords[i][0] for i in to_merge]) / len(to_merge)
        y_avg = sum([all_coords[i][1] for i in to_merge]) / len(to_merge)
        conf = 1.0
        if has_confidence:
            conf = sum([all_coords[i][2] for i in to_merge]) / len(to_merge)
        new_coords.append([x_avg, y_avg, conf])

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
            joints = np.array(pose["keypoints"])
            coco13_joints = merge_coords(
                joints, openpifpaf_to_coco_13, has_confidence=True
            ).flatten()

            poses.append(
                {
                    "video_id": video_id,
                    "frame": frame["frame"],
                    "pose_id": pose_id,
                    "keypoints": coco13_joints,
                    "keypointsopp": joints,
                    "bbox": np.array(pose["bbox"]),
                    "score": pose["score"],
                    "category": pose["category_id"],
                }
            )

    data = [tuple(pose.values()) for pose in poses]

    await self._pool.executemany(
        """
        INSERT INTO pose (
            video_id, frame, pose_idx, keypoints, keypointsopp, bbox, score, category)
            VALUES($1, $2, $3, $4, $5, $6, $7, $8)
        ;
        """,
        data,
    )

    logging.info(f"Loaded {len(poses)} predictions!")


async def load_4dh_predictions(self, video_id: UUID, pkl_path: Path, clear=True) -> None:
    frames = {}

    if clear:
        logging.debug(f"Clearing poses for video {video_id}")
        await self.clear_poses(video_id)

    logging.info(f"Importing data from '{pkl_path}'...")

    frames = joblib.load(pkl_path)

    logging.info(f"Loading data for {len(frames)} frames from '{pkl_path}'...")

    poses = []
    for _, frame in frames.items():
        if not len(frame["2d_joints"]):
            continue

        # XXX TODO we only want the pose data about the tracked poses in each frame;
        # the raw output also contains data about previously tracked poses ("ghosts")
        # that we really don't want to include. Unfortunately the 2d and 3d joints data
        # as well as the conf values and includes these "ghosts", so need to filter those
        # entries out. This can be done by only using the indices of the "tracked_ids"
        # in the larger "tid" list to get the joints and conf data.

        for tracked_id in frame["tracked_ids"]:
            if tracked_id in frame["tid"]:
                pose_idx = frame["tid"].index(tracked_id)
            else:
                logging.info(
                    f"Frame {frame['time']+1}: couldn't find tracked ID {tracked_id} in list of full IDs {frame['tid']}"
                )
                continue

            if frame["conf"][pose_idx] < CONF_THRESH_4DH:
                continue

            img_height, img_width = frame["size"][pose_idx]
            img_size = max(img_width, img_height)
            pose = frame["2d_joints"][pose_idx]
            joints_2d = copy.deepcopy(pose)
            joints_2d = joints_2d.reshape(-1, 2)
            joints_2d *= img_size
            joints_2d[:, 1] -= (
                max(img_width, img_height) - min(img_width, img_height)
            ) / 2

            coco17_joints = merge_coords(joints_2d, phalp_to_coco_17).flatten()

            coco13_joints = merge_coords(joints_2d, phalp_to_coco_13).flatten()

            all_phalp_keypoints = np.array(
                [[coord[0], coord[1], 1.0] for coord in joints_2d]
            ).flatten()

            poses.append(
                {
                    "video_id": video_id,
                    "frame": frame["time"] + 1,
                    "pose_idx": pose_idx,
                    "keypoints": coco13_joints,
                    "keypointsopp": coco17_joints,
                    "keypoints4dh": all_phalp_keypoints,
                    "bbox": np.array(frame["bbox"][pose_idx]),
                    "score": frame["conf"][pose_idx],
                    "category": frame["class_name"][pose_idx],
                    "track_id": tracked_id,
                }
            )

    data = [tuple(pose.values()) for pose in poses]

    await self._pool.executemany(
        """
        INSERT INTO pose (
            video_id, frame, pose_idx, keypoints, keypointsopp, keypoints4dh, bbox, score, category, track_id)
            VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
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
            video_id, frame, local_shot_prob, global_shot_prob, is_shot_boundary, shot)
            VALUES($1, $2, $3, $4, $5, $6)
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
            movement,
            poem_embedding )
            VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
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


async def assign_poem_embeddings(self, poem_data, reindex=True) -> None:
    async with self._pool.acquire() as conn:
        await conn.execute(
            "ALTER TABLE pose ADD COLUMN IF NOT EXISTS poem_embedding vector(16) DEFAULT NULL;"
        )
        await conn.executemany(
            """
                UPDATE pose
                SET poem_embedding = $4
                WHERE video_id = $1 AND frame = $2 AND pose_idx = $3
                ;
            """,
            poem_data,
        )

        if reindex:
            logging.info(
                "Creating approximate index for cosine distance of viewpoint-invariant pose embeddings..."
            )
            await conn.execute(
                """
                CREATE INDEX ON pose
                USING ivfflat (poem_embedding vector_cosine_ops)
                ;
                """,
            )

        return


async def assign_frame_interest(self, frame_interest) -> None:
    async with self._pool.acquire() as conn:
        await conn.execute(
            "ALTER TABLE frame ADD COLUMN IF NOT EXISTS pose_interest FLOAT DEFAULT 0.0;"
        )
        await conn.executemany(
            """
                UPDATE frame
                SET pose_interest = $3
                WHERE video_id = $1 AND frame = $2
                ;
            """,
            frame_interest,
        )

        return


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


async def assign_face_clusters_by_track(self, face_clusters) -> None:
    async with self._pool.acquire() as conn:
        await conn.execute(
            "ALTER TABLE face ADD COLUMN IF NOT EXISTS cluster_id INTEGER DEFAULT NULL;"
        )
        await conn.executemany(
            """
                UPDATE face
                SET cluster_id = $2
                WHERE video_id = $1 AND track_id = $3
                ;
            """,
            face_clusters,
        )

        return


async def assign_movelet_clusters(self, movelet_clusters) -> None:
    async with self._pool.acquire() as conn:
        await conn.execute(
            """
            ALTER TABLE movelet
                ADD COLUMN IF NOT EXISTS cluster_id INTEGER DEFAULT NULL;
            """
        )

        await conn.executemany(
            """
            UPDATE movelet
            SET cluster_id = $5
            WHERE video_id = $1 AND
                  pose_idx = $4 AND
                  start_frame = $2 AND
                  end_frame = $3;
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
    pose_tbl="pose",
) -> None:
    async with self._pool.acquire() as conn:
        await conn.execute(
            f"ALTER TABLE {pose_tbl} ADD COLUMN IF NOT EXISTS {column} {col_type};"
        )

        poses = await conn.fetch(
            f"SELECT * FROM {pose_tbl} WHERE video_id = $1;", video_id
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
