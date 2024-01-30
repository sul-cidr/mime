from uuid import UUID

import asyncpg
import numpy as np


async def get_available_videos(self) -> list:
    return await self._pool.fetch("""SELECT * FROM video_meta;""")


async def get_video_by_id(self, video_id: UUID) -> asyncpg.Record:
    return await self._pool.fetchrow("SELECT * FROM video WHERE id = $1;", video_id)


async def get_video_by_name(self, video_name: str) -> asyncpg.Record:
    return await self._pool.fetchrow(
        "SELECT * FROM video WHERE video_name = $1;", video_name
    )


async def get_pose_data_by_frame(self, video_id: UUID) -> list:
    return await self._pool.fetch(
        """
        SELECT frame,
               pose_ct AS "poseCt",
               track_ct AS "trackCt",
               face_ct AS "faceCt",
               avg_score AS "avgScore",
               is_shot AS "isShot",
               movement,
               pose_interest AS "interest"
           FROM video_frame_meta
           WHERE video_id = $1;
        """,
        video_id,
    )


async def get_pose_data_from_video(self, video_id: UUID) -> list:
    return await self._pool.fetch(
        "SELECT * FROM pose WHERE video_id = $1 ORDER BY frame ASC;",
        video_id,
    )


async def get_video_shot_boundaries(self, video_id: UUID) -> list:
    return await self._pool.fetch(
        "SELECT frame FROM frame WHERE video_id = $1 AND is_shot_boundary ORDER BY frame ASC;",
        video_id,
    )


async def get_clustered_face_data_from_video(self, video_id: UUID) -> list:
    return await self._pool.fetch(
        "SELECT frame, cluster_id, pose_idx, track_id, bbox FROM face WHERE video_id = $1 AND cluster_id IS NOT NULL ORDER BY frame ASC;",
        video_id,
    )


async def get_clustered_movelet_data_from_video(self, video_id: UUID) -> list:
    return await self._pool.fetch(
        "SELECT start_frame, end_frame, cluster_id, track_id, pose_idx FROM movelet WHERE video_id = $1 AND cluster_id IS NOT NULL ORDER BY start_frame ASC;",
        video_id,
    )


async def get_movelet_data_from_video(self, video_id: UUID) -> list:
    return await self._pool.fetch(
        "SELECT * FROM movelet WHERE video_id = $1 ORDER BY start_frame ASC;",
        video_id,
    )


async def get_unique_track_ids_from_video(self, video_id: UUID) -> list:
    return await self._pool.fetch(
        "SELECT UNIQUE track_id FROM pose WHERE video_id = $1;",
        video_id,
    )


async def get_video_id(self, video_name: str) -> asyncpg.Record:
    return await self._pool.fetchval(
        "SELECT id FROM video WHERE video_name = $1;", video_name
    )


async def get_pose_annotations(self, column: str, video_id: UUID) -> list[np.ndarray]:
    annotations = await self._pool.fetch(
        f"SELECT {column} FROM pose WHERE video_id = $1;", video_id
    )
    return [np.array(_[column]) for _ in annotations]


async def get_frame_data(self, video_id: UUID, frame: int) -> list:
    return await self._pool.fetch(
        "SELECT pose.*, frame.shot FROM pose, frame WHERE pose.video_id = $1 AND pose.frame = $2 AND frame.video_id = $1 AND frame.frame = $2;", video_id, frame
    )


async def get_frame_faces(self, video_id: UUID, frame: int) -> list:
    return await self._pool.fetch(
        "SELECT * FROM face WHERE video_id = $1 AND frame = $2;", video_id, frame
    )


async def get_frame_data_range(
    self, video_id: UUID, min_frame: int, max_frame: int
) -> list:
    return await self._pool.fetch(
        "SELECT * FROM pose WHERE video_id = $1 AND frame >= $2 AND frame <= $3;",
        video_id,
        min_frame,
        max_frame,
    )


async def get_poses_with_faces(self, video_id: UUID) -> list:
    return await self._pool.fetch(
        "SELECT pose.video_id as video_id, pose.frame as frame, pose.pose_idx as pose_idx, pose.track_id as track_id, face.bbox as face_bbox, face.confidence as face_confidence, face.embedding as face_embedding, face.landmarks AS face_landmarks FROM pose, face WHERE pose.video_id = $1 AND face.video_id = $1 AND pose.frame = face.frame AND pose.pose_idx = face.pose_idx ORDER BY frame ASC;",
        video_id,
    )


async def get_pose_by_frame_and_track(self, video_id: UUID, frameno: int, track_id: int):
    return await self._pool.fetch(
        "SELECT * FROM pose WHERE video_id = $1 AND frame = $2 AND track_id = $3;",
        video_id,
        frameno,
        track_id,
    )


async def get_face_by_frame_and_track(self, video_id: UUID, frameno: int, track_id: int):
    return await self._pool.fetch(
        "SELECT * FROM face WHERE video_id = $1 AND frame = $2 AND track_id = $3;",
        video_id,
        frameno,
        track_id,
    )


async def get_track_frames(self, video_id: UUID) -> list:
    return await self._pool.fetch(
        "SELECT DISTINCT frame FROM pose WHERE video_id = $1 AND track_id > 0 ORDER BY frame ASC;",
        video_id,
    )


async def get_nearest_poses(
    self, video_id: UUID, frame: int, pose_idx: int, metric="cosine", embedding="norm", avoid_shot=-1, limit=500
) -> list:
    sub_query = f"""
        SELECT {embedding}
        FROM pose
        WHERE video_id = $1 AND frame = $2 AND pose_idx = $3
        """

    distance = {
        "cosine": f"{embedding} <=> ({sub_query})",
        "euclidean": f"{embedding} <-> ({sub_query})",
        "innerproduct": f"{embedding} <#> ({sub_query})",
    }[metric]

    return await self._pool.fetch(
        f"""
        SELECT pose.*, {distance} AS distance, frame.shot AS shot, face.cluster_id AS face_cluster_id FROM pose, frame, face
        WHERE pose.video_id = $1 AND frame.video_id = $1 AND face.video_id = $1 AND face.frame=pose.frame AND face.pose_idx = pose.pose_idx AND pose.frame = frame.frame AND NOT ((pose.frame = $2 AND pose.pose_idx = $3) OR (frame.shot = $4)) ORDER BY distance
        LIMIT $5;
        """,
        video_id,
        frame,
        pose_idx,
        avoid_shot,
        limit,
    )


async def get_movelet_from_pose(
    self, video_id: UUID, frame: int, track_id: int
) -> asyncpg.Record:
    return await self._pool.fetchrow(
        "SELECT * FROM movelet WHERE video_id = $1 AND start_frame <= $2 AND end_frame >= $2 AND track_id = $3;",
        video_id,
        frame,
        track_id,
    )


async def get_nearest_movelets(
    self, video_id: UUID, frame: int, track_id: int, metric="cosine", limit=500
) -> list:
    sub_query = """
        SELECT motion
        FROM movelet
        WHERE video_id = $1 AND start_frame <= $2 AND end_frame >= $2 AND track_id = $3
        LIMIT 1
        """

    distance = {
        "cosine": f"motion <=> ({sub_query})",
        "euclidean": f"motion <-> ({sub_query})",
        "innerproduct": f"motion <#> ({sub_query})",
    }[metric]

    return await self._pool.fetch(
        f"""
        SELECT *, {distance} AS distance FROM movelet
        WHERE video_id = $1 AND NOT (start_frame <= $2 AND end_frame >= $2 AND track_id = $3)
        ORDER BY distance
        LIMIT $4;
        """,
        video_id,
        frame,
        track_id,
        limit,
    )
