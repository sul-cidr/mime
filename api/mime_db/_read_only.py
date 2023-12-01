from uuid import UUID

import asyncpg
import numpy as np


async def get_available_videos(self) -> list:
    videos = await self._pool.fetch(
        """
        SELECT video.*, pose_ct, track_ct, shot_ct, poses_per_frame, face_ct
        FROM video
          LEFT JOIN (
            SELECT video.id, COUNT(*) AS face_ct
            FROM video
              INNER JOIN face ON video.id = face.video_id
            GROUP BY video.id
          ) AS f ON video.id = f.id
          LEFT JOIN (
            SELECT video.id, COUNT(*) filter (where frame.is_shot_boundary) as shot_ct
            FROM video
              INNER JOIN frame ON video.id = frame.video_id
            GROUP BY video.id
          ) as s on video.id = s.id
          LEFT JOIN (
            SELECT video.id,
                   COUNT(*) AS pose_ct,
                   COUNT(DISTINCT pose.track_id) AS track_ct,
                   TRUNC(COUNT(*)::decimal / video.frame_count, 2) AS poses_per_frame
            FROM video
              INNER JOIN pose ON video.id = pose.video_id
              GROUP BY video.id
            ) AS p ON video.id = p.id
        ORDER BY video_name;
        """
    )
    return videos


async def get_video_by_id(self, video_id: UUID) -> asyncpg.Record:
    return await self._pool.fetchrow("SELECT * FROM video WHERE id = $1;", video_id)


async def get_video_by_name(self, video_name: str) -> asyncpg.Record:
    return await self._pool.fetchrow(
        "SELECT * FROM video WHERE video_name = $1;", video_name
    )


async def get_pose_data_by_frame(self, video_id: UUID) -> list:
    return await self._pool.fetch(
        """
        SELECT posefaces.frame,
                posefaces.posect AS "poseCt",
                posefaces.trackct AS "trackCt",
                posefaces.facect AS "faceCt",
                posefaces.avgscore AS "avgScore",
                CAST(frame.is_shot_boundary AS INT) AS "isShot",
                CASE WHEN frame.total_movement = 'NaN' THEN 0.0 ELSE ROUND(frame.total_movement::numeric, 2) END AS "movement"
        FROM (SELECT pose.video_id,
                    pose.frame,
                    count(pose.pose_idx) AS "posect",
                    count(NULLIF(pose.track_id,0)) AS "trackct",
                    count(face.pose_idx) AS "facect",
                    ROUND(AVG(pose.score)::numeric, 2) AS "avgscore"
            FROM pose LEFT JOIN face ON pose.video_id = face.video_id AND pose.frame = face.frame AND pose.pose_idx = face.pose_idx
            WHERE pose.video_id = $1
            GROUP BY pose.video_id, pose.frame
            ORDER BY pose.frame) AS posefaces
        LEFT JOIN frame ON posefaces.video_id = frame.video_id AND posefaces.frame = frame.frame
        ORDER BY posefaces.frame
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
        "SELECT frame, cluster_id, pose_idx, track_id FROM face WHERE video_id = $1 AND cluster_id IS NOT NULL ORDER BY frame ASC;",
        video_id,
    )


async def get_clustered_movelet_data_from_video(self, video_id: UUID) -> list:
    return await self._pool.fetch(
        "SELECT start_frame, end_frame, cluster_id, pose_idx FROM movelet WHERE video_id = $1 AND cluster_id IS NOT NULL ORDER BY start_frame ASC;",
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
        "SELECT * FROM pose WHERE video_id = $1 AND frame = $2;", video_id, frame
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
        "SELECT pose.video_id as video_id, pose.frame as frame, pose.pose_idx as pose_idx, pose.track_id as track_id, face.bbox as face_bbox, face.confidence as face_confidence, face.embedding as face_embedding FROM pose, face WHERE pose.video_id = $1 AND face.video_id = $1 AND pose.frame = face.frame AND pose.pose_idx = face.pose_idx ORDER BY frame ASC;",
        video_id,
    )


async def get_track_frames(self, video_id: UUID) -> list:
    return await self._pool.fetch(
        "SELECT DISTINCT frame FROM pose WHERE video_id = $1 AND track_id > 0 ORDER BY frame ASC;",
        video_id,
    )


async def get_nearest_poses(
    self, video_id: UUID, frame: int, pose_idx: int, metric="cosine", limit=500
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
