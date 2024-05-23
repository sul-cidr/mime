from typing import List, Literal, Set
from uuid import UUID

from lib.pose_utils import get_poem_embedding


async def search_poses(
    self,
    pose_coords: List[int] | List[float],
    search_type: Literal["cosine", "euclidean", "view_invariant", "3d"],
    videos: Set[UUID] | None = None,
    max_distance="Infinity",
    limit=50,
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
        WITH search_results AS(

            SELECT pose.video_id,
                video.video_name,
                pose.frame,
                pose.pose_idx,
                pose.norm, pose.keypoints,
                {distance} AS distance,
                frame.shot AS shot,
                face.cluster_id AS face_cluster_id

            FROM pose, frame, face, video

            WHERE video.id = pose.video_id
              AND frame.video_id = pose.video_id
              AND face.video_id = pose.video_id
              AND face.frame = pose.frame
              AND face.pose_idx = pose.pose_idx
              AND pose.frame = frame.frame
              {additional_where}

            ORDER BY distance

            LIMIT $1
        )

        SELECT * from search_results
        WHERE search_results.distance < $2
        ;
    """,
        limit,
        max_distance,
    )
