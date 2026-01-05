#!/usr/bin/env python3

"""CLI to calculate the average synchronized joint motion per frame.
This is calculated as the average of cosine similarity of the rotational joint
motion vectors for each pair of poses in a frame. Note also that this is based
on movelet data that incorporates a time interval (usually 1/6s). Currently,
the code assigns the degree of sync to the frame at the *start* of the movelet;
this might need to be changed to the frame in the middle of the movelet (or the
end of it)."""

import argparse
import asyncio
import logging

import numpy as np
import pandas as pd
from rich.logging import RichHandler
from sklearn.metrics.pairwise import cosine_similarity

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

    video_data = await db.get_video_by_id(video_id)
    video_fps = video_data["fps"]
    video_frame_count = video_data["frame_count"]

    video_movelets = await db.get_movelet_data_from_video(video_id)
    movelets_df = pd.DataFrame.from_records(
        video_movelets, columns=video_movelets[0].keys()
    )

    start_frames = movelets_df.start_frame.unique()
    all_motion_correlations = []
    frame_joint_motion_corr = {}
    for start_frame in start_frames:
        end_frames = movelets_df[movelets_df["start_frame"] == start_frame][
            "end_frame"
        ].unique()
        if len(end_frames) <= 1:
            continue
        all_joint_motions = []  # rotational velocities
        for end_frame in end_frames:
            if end_frame == start_frame:
                continue
            frame_diff = end_frame - start_frame
            time_elapsed = frame_diff / video_fps
            joint_motions = movelets_df[
                (movelets_df["start_frame"] == start_frame)
                & (movelets_df["end_frame"] == end_frame)
            ]["joint_motion3d"].values
            # print(start_frame, end_frame, joint_motions)
            for joint_motion in joint_motions:
                joint_velocities = joint_motion / time_elapsed
                if len(joint_velocities.nonzero()[0]) > 0:
                    all_joint_motions.append(joint_velocities)

        if len(all_joint_motions) <= 1:
            continue

        velocity_correlations = cosine_similarity(
            np.array(all_joint_motions)
        )  # np.corrcoef(all_joint_motions)
        corrs_to_avg = []
        for corr in velocity_correlations[0][1:]:
            corrs_to_avg.append(corr)

        frame_joint_motion_corr[start_frame] = np.mean(corrs_to_avg)

    for f in range(1, max(max(frame_joint_motion_corr.keys()), video_frame_count + 1)):
        if f in frame_joint_motion_corr:
            all_motion_correlations.append([video_id, f, frame_joint_motion_corr[f]])
        else:
            all_motion_correlations.append([video_id, f, 0])

    logging.info("ASSIGNING MOTION CORRELATION LEVELS TO FRAMES IN DB")
    await db.assign_frame_sync_motion(all_motion_correlations)


if __name__ == "__main__":
    asyncio.run(main())
