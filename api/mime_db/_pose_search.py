from typing import List, Literal, Set
from uuid import UUID

from lib.pose_utils import get_poem_embedding


async def search_poses(
    self,
    pose_coords: List[int] | List[float],
    search_type: Literal["cosine", "euclidean", "view_invariant", "3d"],
    videos: Set[UUID] | None = None,
    exclude_within_frames: int = 30,
    limit: int = 50,
) -> list:
    """Search for poses in the database"""

    additional_where = (
        ""
        if videos is None
        else f"""AND pose.video_id IN ({",".join(f"'{v}'" for v in list(videos))})"""
    )

    (metric, embedding) = {
        "cosine": ("cosine", "norm"),
        "euclidean": ("euclidean", "norm"),
        "view_invariant": ("cosine", "poem_embedding"),
        "3d": ("cosine", "global3d_coco13"),
    }[search_type]

    if search_type == "3d":
        pose_coords = list(map(float, pose_coords))

    if search_type == "view_invariant":
        pose_coords = get_poem_embedding(pose_coords)

    distance = {
        "cosine": f"{embedding} <=> '{pose_coords}'",
        "euclidean": f"{embedding} <-> '{pose_coords}'",
        "innerproduct": f"({embedding} <#> '{pose_coords}' * -1",
    }[metric]

    return await self._pool.fetch(
        f"""
        WITH ranked_poses AS (

            SELECT pose.video_id,
                video.video_name,
                pose.frame,
                pose.pose_idx,
                pose.norm,
                pose.keypoints,
                {distance} AS distance,
                RANK() OVER (ORDER BY {distance}) AS rank

            FROM pose, video

            WHERE video.id = pose.video_id
              {additional_where}

            ORDER BY distance
            LIMIT 50000
        )

        SELECT video_id,
               video_name,
               frame,
               pose_idx,
               norm,
               keypoints,
               distance,
               rank
        FROM ranked_poses
        WHERE NOT EXISTS (
            SELECT 1
            FROM ranked_poses rp2
            WHERE rp2.rank < ranked_poses.rank
            and rp2.video_id = ranked_poses.video_id
            and rp2.pose_idx = ranked_poses.pose_idx
            and ABS(rp2.frame - ranked_poses.frame) < $2
        )
        ORDER BY distance
        LIMIT $1
        ;
    """,
        limit,
        exclude_within_frames,
    )
