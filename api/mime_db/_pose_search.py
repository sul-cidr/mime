from typing import List, Literal, Set
from uuid import UUID

import numpy as np
from tsmoothie.smoother import GaussianSmoother

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
        "innerproduct": f"({embedding} <#> '{pose_coords}') * -1",
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
                pose.bbox,
                {distance} AS distance,
                RANK() OVER (ORDER BY {distance}) AS rank

            FROM pose, video

            WHERE video.id = pose.video_id
              {additional_where}

            ORDER BY distance
            LIMIT 50000
        ),

        matches as (
            SELECT ranked_poses.video_id,
                video_name,
                ranked_poses.frame,
                ranked_poses.pose_idx,
                norm,
                keypoints,
                ranked_poses.bbox,
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
        )

        SELECT matches.*,
               rhand.keypoints2d AS rh_keypoints2d,
               rhand.global_orient AS rh_global_orient,
               lhand.keypoints2d AS lh_keypoints2d,
               lhand.global_orient AS lh_global_orient
        FROM matches
        LEFT JOIN hand AS rhand
            ON matches.video_id = rhand.video_id
            AND matches.pose_idx = rhand.pose_idx
            AND matches.frame = rhand.frame
            AND rhand.is_right = 't'
        LEFT JOIN hand AS lhand
            ON matches.video_id = lhand.video_id
            AND matches.pose_idx = lhand.pose_idx
            AND matches.frame = lhand.frame
            AND lhand.is_right = 'f'
        ;
    """,
        limit,
        exclude_within_frames,
    )

async def pose_or_hand_prevalence(
    self,
    video: UUID,
    pose_or_hand: Literal["pose", "hand"],
    pose_coords: List[int] | List[float],
    search_type: Literal["cosine", "euclidean", "view_invariant", "3d", "joint_angles3d", "class_weights"],
) -> list:
    """Search for poses in the database"""

    (metric, embedding) = {
        "cosine": ("cosine", "norm"),
        "euclidean": ("euclidean", "norm"),
        "view_invariant": ("cosine", "poem_embedding"),
        "3d": ("cosine", "global3d_coco13"),
        "joint_angles3d": ("cosine", "joint_angles3d"),
        "class_weights": ("cosine", "class_weights")
    }[search_type]

    if search_type == "3d":
        pose_coords = list(map(float, pose_coords))

    if search_type == "view_invariant":
        pose_coords = get_poem_embedding(pose_coords)

    distance = {
        "cosine": f"{embedding} <=> '{pose_coords}'",
        "euclidean": f"{embedding} <-> '{pose_coords}'",
        "innerproduct": f"({embedding} <#> '{pose_coords}') * -1",
    }[metric]

    all_frames = await self._pool.fetch(
        """
        SELECT DISTINCT frame FROM frame WHERE video_id = $1 ORDER BY frame ASC;
        """,
        video
    )

    avg_frame_sims = await self._pool.fetch(
        f"""
        SELECT
            pose.frame,
            1 - AVG({distance}) AS similarity
        FROM {pose_or_hand}
        WHERE {pose_or_hand}.video_id = $1
        GROUP BY frame
        ORDER BY frame
        ;
    """,
        video,
    )

    sims_by_frame = {}
    for frame in avg_frame_sims:
        sims_by_frame[frame["frame"]] = frame["similarity"]

    all_frame_ids = [] # This should eventually just be 1 ... total frames in video
    all_frame_sims = []
    for frame in all_frames:
        all_frame_ids.append(frame["frame"])
        if frame["frame"] in sims_by_frame:
            all_frame_sims.append(sims_by_frame[frame["frame"]])
        else:
            all_frame_sims.append(0)

    # Try to include a minimum number of frames in the analysis, so reduce the
    # inter-sample distance if the video is short
    FRAMES_TARGET = 1800
    MAX_SAMPLE_GAP = 240
    WINDOW_SIZE = 500

    sample_gap = min(MAX_SAMPLE_GAP, max(1, round(len(all_frame_sims) / FRAMES_TARGET)))
    
    midpt = int(WINDOW_SIZE / 2)
    step = 1 / (midpt+1)
    weights = [i * step for i in range(1, midpt+2)]
    weights.extend(list(reversed(weights))[1:])

    weights = np.ones(WINDOW_SIZE) / WINDOW_SIZE

    ma_frame_sims = np.convolve(all_frame_sims, weights, mode="same")

    smoother = GaussianSmoother(n_knots=6, sigma=0.1)
    smoother.smooth(all_frame_sims)
    gaussian_frame_sims = smoother.smooth_data[0]

    output_frames = []

    for f in range(len((all_frame_sims))):
        if f % sample_gap == 0 or f == len(all_frame_sims)-1:
            output_frames.append({"frame": f+1, "similarity": all_frame_sims[f], "moving_average": ma_frame_sims[f], "gaussian": gaussian_frame_sims[f]})

    return output_frames
