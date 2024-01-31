#!/usr/bin/env python3

"""CLI to calculate each frame's avg distance from the global avg pose for a video."""

import argparse
import asyncio
import logging

import numpy as np
from rich.logging import RichHandler
from scipy.spatial.distance import cosine  # , euclidean

from lib.pose_drawing import *
from mime_db import MimeDb

DEFAULT_CLUSTERS = 15  # Expected number of pose clusters


async def main() -> None:
    """Command-line entry-point."""

    parser = argparse.ArgumentParser(description="Description: {}".format(__doc__))
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Enable debug logging",
    )

    parser.add_argument(
        "--video-name",
        action="store",
        required=True,
        help="The name of the video file (with extension)",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    logging.info("CALCULATING PER-FRAME POSE INTEREST")

    # Connect to the database
    db = await MimeDb.create()

    # Get video ID
    video_id = await db.get_video_id(args.video_name)

    video_poses = await db.get_pose_data_from_video(video_id)

    all_pose_coords = []

    for pose_data in video_poses:
        all_pose_coords.append(pose_data["norm"])

    mean_global_pose = np.mean(all_pose_coords, axis=0)

    mean_pose = [
        [mean_global_pose[x], mean_global_pose[x + 1], 1]
        for x in range(0, len(mean_global_pose), 2)
    ]

    mean_pose_img = draw_normalized_and_unflattened_pose(mean_pose)
    mean_pose_img.save(f"pose_cluster_images/{args.video_name}.png")

    all_distances = []

    frame_interest = {}

    last_frame = None
    current_deviations = []
    for pose_data in video_poses:
        if (
            last_frame is not None
            and last_frame != pose_data["frame"]
            and len(current_deviations) > 0
        ):
            frame_interest[pose_data["frame"]] = np.mean(current_deviations)
            all_distances.append(np.mean(current_deviations))

            current_deviations = []

        # current_deviations.append(euclidean(pose_data["norm"], mean_global_pose))
        current_deviations.append(cosine(pose_data["norm"], mean_global_pose))

        last_frame = pose_data["frame"]

    max_distance = max(all_distances)

    normalized_frame_interest = []

    for frame in frame_interest:
        normalized_frame_interest.append(
            [video_id, frame, round(frame_interest[frame] / max_distance, 2)]
        )

    logging.info(
        f"DIST STATS: MEAN {np.mean(all_distances)} MEDIAN {np.median(all_distances)} STDEV {np.std(all_distances)} MAX {np.max(all_distances)} MIN {np.min(all_distances)}"
    )

    await db.assign_frame_interest(normalized_frame_interest)


if __name__ == "__main__":
    asyncio.run(main())
