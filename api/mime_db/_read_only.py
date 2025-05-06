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
               track_ct AS "trackCt",
               face_ct AS "faceCt",
               hand_ct AS "handCt",
               avg_score AS "avgScore",
               is_shot AS "isShot",
               movement,
               movement3d,
               pose_interest,
               action_interest
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


async def get_video_shots(self, video_id: UUID) -> list:
    return await self._pool.fetch(
        "SELECT frame, shot FROM frame WHERE video_id = $1 ORDER BY frame ASC;",
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
        "SELECT pose.*, frame.shot, frame.pose_interest, frame.action_interest FROM pose, frame WHERE pose.video_id = $1 AND pose.frame = $2 AND frame.video_id = $1 AND frame.frame = $2;",
        video_id,
        frame,
    )


async def get_frame_faces(self, video_id: UUID, frame: int) -> list:
    return await self._pool.fetch(
        "SELECT * FROM face WHERE video_id = $1 AND frame = $2;", video_id, frame
    )


async def get_frame_hands(self, video_id: UUID, frame: int) -> list:
    return await self._pool.fetch(
        "SELECT * FROM hand WHERE video_id = $1 AND frame = $2;", video_id, frame
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


async def search_by_pose(
    self,
    video_param: UUID | str,
    pose_coords: list,
    metric="cosine",
    embedding="norm",
    max_distance="Infinity",
    limit=500,
) -> list:
    if isinstance(video_param, str) and video_param.find("ALL|") != -1:
        pose_subquery = "TRUE"
    else:
        pose_subquery = f"pose.video_id = '{video_param}'"

    distance = {
        "cosine": f"{embedding} <=> '{pose_coords}'",
        "euclidean": f"{embedding} <-> '{pose_coords}'",
        "innerproduct": f"({embedding} <#> '{pose_coords}' * -1",
    }[metric]

    return await self._pool.fetch(
        f"""
    WITH search_results AS(
        SELECT pose.video_id, video.video_name, pose.frame, pose.pose_idx, pose.norm, pose.keypoints, {distance} AS distance, frame.shot AS shot, face.cluster_id AS face_cluster_id FROM pose, frame, face, video
        WHERE {pose_subquery} AND video.id = pose.video_id AND frame.video_id = pose.video_id AND face.video_id = pose.video_id AND face.frame = pose.frame AND face.pose_idx = pose.pose_idx AND pose.frame = frame.frame ORDER BY distance
        LIMIT $1
    )
    SELECT * from search_results where search_results.distance < {max_distance}
    """,
        limit,
    )


async def get_nearest_poses(
    self,
    video_param: UUID | str,
    frame: int,
    pose_idx: int,
    metric="cosine",
    embedding="norm",
    max_distance="Infinity",
    avoid_shot=-1,
    limit=500,
) -> list:
    if isinstance(video_param, str) and video_param.find("ALL|") != -1:
        pose_subquery = "TRUE"
        distance_subquery = f"""
            SELECT {embedding}
            FROM pose
            WHERE video_id = '{video_param.split("|")[1]}' AND frame = $1 AND pose_idx = $2
            """
    else:
        pose_subquery = f"pose.video_id = '{video_param}'"
        distance_subquery = f"""
            SELECT {embedding}
            FROM pose
            WHERE video_id = '{video_param}' AND frame = $1 AND pose_idx = $2
        """

    distance = {
        "cosine": f"{embedding} <=> ({distance_subquery})",
        "euclidean": f"{embedding} <-> ({distance_subquery})",
        "innerproduct": f"({embedding} <#> ({distance_subquery}) * -1",
    }[metric]

    return await self._pool.fetch(
        f"""
        WITH search_results AS (
          SELECT pose.video_id,
                 video.video_name,
                 pose.frame,
                 pose.pose_idx,
                 pose.norm,
                 pose.keypoints,
                 {distance} AS distance,
                 frame.shot AS shot,
                 face.cluster_id AS face_cluster_id
          FROM pose
            INNER JOIN video ON video.id = pose.video_id
            INNER JOIN frame ON frame.video_id = pose.video_id
            AND frame.frame = pose.frame
            LEFT JOIN face ON face.video_id = pose.video_id
                          AND face.frame = pose.frame
                          AND face.pose_idx = pose.pose_idx
          WHERE {pose_subquery}
            AND NOT ((pose.frame = $1 AND pose.pose_idx = $2) OR frame.shot = $3)
          ORDER BY distance
          LIMIT $4
        )
        SELECT * FROM search_results WHERE search_results.distance < {max_distance}
        """,
        frame,
        pose_idx,
        avoid_shot,
        limit,
    )


async def get_nearest_hands(
    self,
    video_param: UUID | str,
    frame: int,
    pose_idx: int,
    is_right: bool,
    metric="cosine",
    embedding="joint_angles3d",
    max_distance="Infinity",
    avoid_shot=-1,
    limit=500,
) -> list:
    if isinstance(video_param, str) and video_param.find("ALL|") != -1:
        hand_subquery = "TRUE"
        distance_subquery = f"""
            SELECT {embedding}
            FROM hand
            WHERE video_id = '{video_param.split("|")[1]}' AND frame = $1 AND pose_idx = $2 and is_right = {is_right}
            """
    else:
        hand_subquery = f"hand.video_id = '{video_param}'"
        distance_subquery = f"""
            SELECT {embedding}
            FROM hand
            WHERE video_id = '{video_param}' AND frame = $1 AND pose_idx = $2 and is_right = {is_right}
        """

    distance = {
        "cosine": f"{embedding} <=> ({distance_subquery})",
        "euclidean": f"{embedding} <-> ({distance_subquery})",
        "innerproduct": f"({embedding} <#> ({distance_subquery}) * -1",
    }[metric]

    # if is_right is True:
    #     handedness_clause = "search_results.keypoints2d AS rh_keypoints_2d"
    # else:
    #     handedness_clause = "search_results.keypoints2d AS lh_keypoints_2d"

    return await self._pool.fetch(
        f"""
        WITH hand_results AS(
            WITH search_results AS(
                SELECT hand.video_id, video.video_name, hand.frame, hand.pose_idx, hand.is_right, pose.norm, pose.keypoints, hand.keypoints2d, hand.is_right AS search_is_right, hand.global_orient AS hand_global_orient, {distance} AS distance, frame.shot AS shot FROM hand, pose, frame, video
                WHERE {hand_subquery} AND video.id = hand.video_id AND pose.video_id = hand.video_id AND frame.video_id = hand.video_id AND pose.frame = hand.frame AND pose.pose_idx = hand.pose_idx AND frame.frame = hand.frame AND NOT ((hand.frame = $1 AND hand.pose_idx = $2) OR frame.shot = $3) ORDER BY distance
                LIMIT $4
            )
            SELECT search_results.* FROM search_results WHERE search_results.distance < {max_distance}
        )
        SELECT hand_results.*, face.landmarks AS face_landmarks, face.cluster_id AS face_cluster_id FROM hand_results LEFT JOIN face ON face.video_id = hand_results.video_id AND face.frame = hand_results.frame AND face.pose_idx = hand_results.pose_idx
        """,
        frame,
        pose_idx,
        avoid_shot,
        limit,
    )


async def get_nearest_actions(
    self,
    video_param: UUID | str,
    frame: int,
    track_id: int,
    max_distance="Infinity",
    avoid_shot=-1,
    limit=500,
) -> list:
    if isinstance(video_param, str) and video_param.find("ALL|") != -1:
        pose_subquery = "TRUE"
        distance_subquery = f"""ava_action <=> (SELECT ava_action FROM pose WHERE video_id = '{video_param.split("|")[1]}' AND frame = $1 AND track_id = $2)"""
    else:
        pose_subquery = f"pose.video_id = '{video_param}'"
        distance_subquery = f"""ava_action <=> (SELECT ava_action FROM pose WHERE video_id = '{video_param}' AND frame = $1 AND track_id = $2)"""

    return await self._pool.fetch(
        f"""
        WITH action_results AS(
            WITH search_results AS(
                SELECT pose.video_id, video.video_name, pose.frame, pose.pose_idx, pose.track_id, pose.norm, pose.keypoints, {distance_subquery} AS distance, pose.ava_action AS ava_action, pose.action_labels AS action_labels, frame.shot AS shot FROM pose, frame, video
                WHERE {pose_subquery} AND video.id=pose.video_id AND frame.video_id = pose.video_id AND pose.frame = frame.frame AND NOT (frame.shot = $3 OR (pose.frame = $1 AND pose.track_id = $2))
                ORDER BY distance
                LIMIT $4
            )
            SELECT * from search_results where search_results.distance < $5
        )
        SELECT action_results.*, face.cluster_id AS face_cluster_id FROM action_results LEFT JOIN face ON face.video_id = action_results.video_id AND face.frame = action_results.frame AND face.pose_idx = action_results.pose_idx
        """,
        frame,
        track_id,
        avoid_shot,
        limit,
        max_distance,
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
    self,
    video_id: UUID,
    frame: int,
    track_id: int,
    metric="cosine",
    max_distance="Infinity",
    avoid_shot=-1,
    limit=500,
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
        with movelet_results AS
            WITH search_results AS(
                SELECT movelet.video_id, movelet.start_frame, movelet.end_frame, movelet.pose_idx, movelet.track_id, movelet.norm, movelet.prev_norm, {distance} AS distance, frame.shot AS shot FROM movelet, frame
                WHERE movelet.video_id = $1 AND frame.video_id = $1 AND movelet.start_frame = frame.frame AND NOT ((movelet.start_frame <= $2 AND movelet.end_frame >= $2) OR frame.shot = $4 OR (movelet.start_frame = $2 AND movelet.track_id = $3))
                ORDER BY distance
                LIMIT $5
            )
            SELECT * from search_results where search_results.distance < {max_distance}
        )
        SELECT movelet_results.*, face.cluster_id AS face_cluster_id FROM movelet_results LEFT JOIN face ON face.video_id = movelet_results.video_id AND face.frame = movelet_results.start_frame AND face.pose_idx = movelet_results.pose_idx
        """,
        video_id,
        frame,
        track_id,
        avoid_shot,
        limit,
    )