#!/usr/bin/env python3

"""CLI to calculate the average distance of some attribute of a frame (e.g.,
the poses in it) from the global avg of that attribute for a video. This value
is then presented as a proxy for the "interest" of that attribute across all
frames in the vide. The two options available (currently) are pose and action.
Note that the normalized pose data is generally always available but the action
recognition data may not be; if that option is selected and the data in the DB
are null, this script will fail with an error."""

import argparse
import asyncio
import logging

import numpy as np
from rich.logging import RichHandler
from scipy.spatial.distance import cosine  # , euclidean

from lib.pose_drawing import draw_normalized_and_unflattened_pose
from mime_db import MimeDb


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

    parser.add_argument(
        "--metric",
        action="store",
        required=True,
        default="pose",
        help="[pose|action] (default pose)",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    # Connect to the database
    db = await MimeDb.create()

    # Get video ID
    video_id = await db.get_video_id(args.video_name)
    # and poses
    video_poses = await db.get_pose_data_from_video(video_id)

    if args.metric == "pose":
        logging.info("CALCULATING POSE AND FRAME POSE INTEREST")
        db_key = "norm"
    else:
        logging.info("CALCULATING POSE AND FRAME ACTION INTEREST")
        db_key = "ava_action"

    all_vectors = []

    for pose_data in video_poses:
        all_vectors.append(pose_data[db_key])

    mean_global_vector = np.mean(all_vectors, axis=0)

    mean_vector = [
        [mean_global_vector[x], mean_global_vector[x + 1], 1]
        for x in range(0, len(mean_global_vector), 2)
    ]

    if args.metric == "pose":
        mean_pose_img = draw_normalized_and_unflattened_pose(mean_vector)
        mean_pose_img.save(f"pose_cluster_images/{args.video_name}.png")

    all_distances = []

    pose_interest = {}
    frame_interest = {}

    last_frame = None
    current_deviations = []
    for pose_data in video_poses:
        if (
            last_frame is not None
            and last_frame != pose_data["frame"]
            and len(current_deviations) > 0
        ):
            # ? Use np.max() or np.mean() (or median?) Probably max is best...
            mean_deviation = np.mean(current_deviations)
            frame_interest[pose_data["frame"]] = mean_deviation
            all_distances.append(mean_deviation)

            current_deviations = []

        # current_deviations.append(euclidean(pose_data[db_key], mean_global_pose))
        pose_deviation = cosine(pose_data[db_key], mean_global_vector)
        if pose_data["frame"] in pose_interest:
            pose_interest[pose_data["frame"]][pose_data["pose_idx"]] = pose_deviation
        else:
            pose_interest[pose_data["frame"]] = {pose_data["pose_idx"]: pose_deviation}

        current_deviations.append(pose_deviation)

        last_frame = pose_data["frame"]

    max_distance = max(all_distances)

    normalized_frame_interest = []
    normalized_pose_interest = []

    for frame in frame_interest:
        normalized_frame_interest.append(
            [video_id, frame, round(frame_interest[frame] / max_distance, 2)]
        )
        for pose_idx in pose_interest[frame]:
            normalized_pose_interest.append(
                [
                    video_id,
                    frame,
                    pose_idx,
                    round(pose_interest[frame][pose_idx] / max_distance, 2),
                ]
            )

    logging.info(
        f"DIST STATS: MEAN {np.mean(all_distances)} MEDIAN {np.median(all_distances)} STDEV {np.std(all_distances)} MAX {np.max(all_distances)} MIN {np.min(all_distances)}"
    )

    logging.info("ASSIGNING INTEREST LEVELS TO FRAMES IN DB")
    await db.assign_frame_interest(normalized_frame_interest, args.metric)
    logging.info("ASSIGNING INTEREST LEVELS TO POSES IN DB")
    await db.assign_pose_interest(normalized_pose_interest, args.metric)


if __name__ == "__main__":
    asyncio.run(main())
