from typing import List, Literal, Set
from uuid import UUID


async def search_hands(
    self,
    embedding: List[int] | List[float],
    search_type: Literal["joint_angles3d", "embedding", "global3d"],
    videos: Set[UUID] | None = None,
    exclude_within_frames: int = 30,
    limit: int = 50,
) -> list:
    """Search for hands in the database"""

    where_clause = (
        ""
        if videos is None
        else f"""WHERE hand.video_id IN ({",".join(f"'{v}'" for v in list(videos))})"""
    )

    distance = {
        "joint_angles3d": f"joint_angles3d <=> '{embedding}'",
        "embedding": f"class_weights <=> '{embedding}'",
        "global3d": f"rectified3d <=> '{embedding}'",
    }[search_type]

    return await self._pool.fetch(
        f"""
        WITH ranked_hands AS (
            SELECT hand.video_id,
                hand.frame,
                hand.pose_idx,
                {distance} AS distance,
                RANK() OVER (ORDER BY {distance}) AS rank
            FROM hand
            {where_clause}
            ORDER BY distance
            LIMIT 50000
        ),

        matches AS (
            SELECT *
            FROM ranked_hands
            WHERE NOT EXISTS (
                SELECT 1
                FROM ranked_hands rh2
                WHERE rh2.rank < ranked_hands.rank
                and rh2.video_id = ranked_hands.video_id
                and rh2.pose_idx = ranked_hands.pose_idx
                and ABS(rh2.frame - ranked_hands.frame) < $2
            )
            ORDER BY distance
            LIMIT $1
        )

        SELECT matches.*,
               video.video_name,
               pose.norm,
               pose.keypoints,
               pose.bbox,
               rHand.keypoints2d AS rh_keypoints2d,
               rHand.global_orient AS rh_global_orient,
               lHand.keypoints2d AS lh_keypoints2d,
               lHand.global_orient AS lh_global_orient

        FROM matches
            LEFT JOIN hand AS rHand
                ON matches.video_id = rHand.video_id
                AND matches.pose_idx = rHand.pose_idx
                AND matches.frame = rHand.frame
                AND rHand.is_right = 't'

            LEFT JOIN hand AS lHand
                ON matches.video_id = lHand.video_id
                AND matches.pose_idx = lHand.pose_idx
                AND matches.frame = lHand.frame
                AND lHand.is_right = 'f',

            pose, video

        WHERE matches.video_id = pose.video_id
            AND matches.frame = pose.frame
            AND matches.pose_idx = pose.pose_idx
            AND matches.video_id = video.id
        ;
        """,
        limit,
        exclude_within_frames,
    )
