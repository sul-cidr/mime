#!/usr/bin/env python3

"""CLI to add motion tracking data to OpenPifPaf pose data for a video in the db."""

import argparse
import asyncio
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from rich.logging import RichHandler
from sklearn.metrics.pairwise import nan_euclidean_distances

from mime_db import MimeDb

TICK_INTERVAL = 0.1666667  # 1/6 of a second


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
        "--drop",
        action="store_true",
        default=False,
        help="Drop (if existing) and recreate tables",
    )

    parser.add_argument("--video-path", action="store", required=True)

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    # This should really just be the name of the video, since its pose data
    # must already be in the DB by the time this is run
    video_path = Path(args.video_path)

    # Connect to the database
    db = await MimeDb.create(drop=args.drop)

    # Get video metadata and add to database
    video_name = video_path.name

    video_id = await db.get_video_id(video_name)

    video_metadata = await db.get_video_by_id(video_id)

    logging.info("Computing motion movelets for pose tracks")

    track_data = await db.get_pose_data_from_video(video_id)

    tracks_df = pd.DataFrame.from_records(track_data, columns=track_data[0].keys())

    # XXX Need to adjust if track_id allowed to be null
    tracks_df = tracks_df[tracks_df["track_id"] != 0]

    tracks_df["timecode"] = tracks_df["frame"] / video_metadata["fps"]

    def assign_tick_values(timecodes):
        return [int((code - timecodes.iloc[0]) / TICK_INTERVAL) for code in timecodes]

    tracks_df["tick"] = tracks_df.groupby(["track_id"])["timecode"].transform(
        assign_tick_values
    )

    def avg_pose_data(poses):
        poses_with_nans = [np.where(pose == -1, np.nan, pose) for pose in poses]
        data_mean = np.nanmean(poses_with_nans, axis=0)
        return [data_mean] * len(poses)

    norm_coords = 26
    global3d_coco13_coords = 39

    tracks_df["tick_norm"] = tracks_df.groupby(["track_id", "tick"])["norm"].transform(
        avg_pose_data
    )

    # The pose-invariant embedding is used subsequently in similarity
    # comparisons of representative poses of movelet tracks (but it's not
    # currently used for motion/gesture quantification).
    tracks_df["tick_poem"] = tracks_df.groupby(["track_id", "tick"])[
        "poem_embedding"
    ].transform(avg_pose_data)

    tracks_df["tick_global3d_coco13"] = tracks_df.groupby(["track_id", "tick"])[
        "global3d_coco13"
    ].transform(avg_pose_data)

    # XXX It's important to know exactly when the track/motion begins, which
    # is why we take the minimum of the tick's timecodes, but this is a slight
    # mismatch with the tick norm calculations above, which will tend to settle
    # upon the "middle" of the tick. But maybe it's OK -- we're talking quite
    # small fractions of a second.
    tracks_df["tick_start_timecode"] = tracks_df.groupby(["track_id", "tick"])[
        "timecode"
    ].transform(lambda timecodes: [np.min(timecodes, axis=0)] * len(timecodes))

    tracks_df["tick_start_frame"] = tracks_df.groupby(["track_id", "tick"])[
        "frame"
    ].transform(lambda frames: [np.min(frames, axis=0)] * len(frames))

    tracks_df["tick_end_timecode"] = tracks_df.groupby(["track_id", "tick"])[
        "timecode"
    ].transform(lambda timecodes: [np.max(timecodes, axis=0)] * len(timecodes))

    tracks_df["tick_end_frame"] = tracks_df.groupby(["track_id", "tick"])[
        "frame"
    ].transform(lambda frames: [np.max(frames, axis=0)] * len(frames))

    tracks_tick_df = tracks_df.groupby(["track_id", "tick"]).first().reset_index()

    tracks_tick_df["tick_timediff"] = tracks_tick_df.groupby(["track_id"])[
        "tick_start_timecode"
    ].diff()

    tracks_tick_df["prev_tick_norm"] = tracks_tick_df.groupby(["track_id"])[
        "tick_norm"
    ].shift(1)

    tracks_tick_df["prev_tick_norm"] = tracks_tick_df["prev_tick_norm"].apply(
        lambda x: [np.nan] * norm_coords if isinstance(x, float) else x
    )

    tracks_tick_df["prev_tick_global3d_coco13"] = tracks_tick_df.groupby(["track_id"])[
        "tick_global3d_coco13"
    ].shift(1)

    tracks_tick_df["prev_tick_global3d_coco13"] = tracks_tick_df[
        "prev_tick_global3d_coco13"
    ].apply(lambda x: [np.nan] * global3d_coco13_coords if isinstance(x, float) else x)

    # For 2D "norm" coordinates

    def compute_motion_vector(timediff, last_norm, norm):
        if np.isnan(timediff) or timediff == 0 or isinstance(last_norm, float):
            return [np.nan] * norm_coords
        normdiff = []
        for i in range(0, norm_coords, 2):
            last_x = last_norm[i]
            last_y = last_norm[i + 1]
            this_x = norm[i]
            this_y = norm[i + 1]
            if last_x == -1 or last_y == -1 or this_x == -1 or this_y == -1:
                x_vel = np.nan
                y_vel = np.nan
            else:
                x_vel = last_x - this_x
                y_vel = last_y - this_y
            normdiff.extend([x_vel, y_vel])
        return normdiff

    def compute_movement(timediff, last_norm, norm):
        if np.isnan(timediff) or timediff == 0 or isinstance(last_norm, float):
            return 0  # usually this is the first frame in the movelet
        motion = nan_euclidean_distances([last_norm], [norm])[0]
        return motion / timediff

    tracks_tick_df["motion_vector"] = tracks_tick_df.apply(
        lambda row: compute_motion_vector(
            row["tick_timediff"], row["prev_tick_norm"], row["tick_norm"]
        ),
        axis=1,
    )

    tracks_tick_df["movement"] = tracks_tick_df.apply(
        lambda row: compute_movement(
            row["tick_timediff"], row["prev_tick_norm"], row["tick_norm"]
        ),
        axis=1,
    )

    tracks_tick_df["movelet_vector"] = tracks_tick_df["tick_norm"].apply(
        list
    ) + tracks_tick_df["motion_vector"].apply(list)

    # For 3D "global" coordinates

    def compute_motion_vector_3d(timediff, last_pose, pose):
        if np.isnan(timediff) or timediff == 0 or isinstance(last_pose, float):
            return [np.nan] * norm_coords
        global3d_coco13_diff = []
        for i in range(0, global3d_coco13_coords, 3):
            last_x = last_pose[i]
            last_y = last_pose[i + 1]
            last_z = last_pose[i + 2]
            this_x = pose[i]
            this_y = pose[i + 1]
            this_z = pose[i + 2]
            if (
                last_x == -1
                or last_y == -1
                or last_z == -1
                or this_x == -1
                or this_y == -1
                or this_z == -1
            ):
                x_vel = np.nan
                y_vel = np.nan
                z_vel = np.nan
            else:
                x_vel = last_x - this_x
                y_vel = last_y - this_y
                z_vel = last_z - this_z
            global3d_coco13_diff.extend([x_vel, y_vel, z_vel])
        return global3d_coco13_diff

    def compute_movement_3d(timediff, last_pose, pose):
        if np.isnan(timediff) or timediff == 0 or isinstance(last_pose, float):
            return 0  # usually this is the first frame in the movelet
        motion = nan_euclidean_distances([last_pose], [pose])[0]
        return motion / timediff

    tracks_tick_df["motion_vector_3d"] = tracks_tick_df.apply(
        lambda row: compute_motion_vector_3d(
            row["tick_timediff"],
            row["prev_tick_global3d_coco13"],
            row["tick_global3d_coco13"],
        ),
        axis=1,
    )

    tracks_tick_df["movement_3d"] = tracks_tick_df.apply(
        lambda row: compute_movement_3d(
            row["tick_timediff"],
            row["prev_tick_global3d_coco13"],
            row["tick_global3d_coco13"],
        ),
        axis=1,
    )

    # This is only used in 2D for a visualization, and that viz isn't very useful anyway
    # tracks_tick_df["movelet_vector_3d"] = tracks_tick_df["tick_global3d_coco13"].apply(
    #     list
    # ) + tracks_tick_df["motion_vector_3d"].apply(list)

    # Clean up NaNs for all fields (2D and 3D, and POEM)

    tracks_tick_df["movelet_vector"] = tracks_tick_df["movelet_vector"].apply(
        lambda x: np.nan_to_num(x, nan=-1)
    )

    tracks_tick_df["prev_tick_norm"] = tracks_tick_df["prev_tick_norm"].apply(
        lambda x: np.nan_to_num(x, nan=-1)
    )

    tracks_tick_df["tick_norm"] = tracks_tick_df["tick_norm"].apply(
        lambda x: np.nan_to_num(x, nan=-1)
    )

    # This is only used in 2D for a visualization, and that viz isn't very useful anyway
    # tracks_tick_df["movelet_vector_3d"] = tracks_tick_df["movelet_vector_3d"].apply(
    #     lambda x: np.nan_to_num(x, nan=-1)
    # )

    tracks_tick_df["prev_tick_global3d_coco13"] = tracks_tick_df[
        "prev_tick_global3d_coco13"
    ].apply(lambda x: np.nan_to_num(x, nan=-1))

    tracks_tick_df["tick_global3d_coco13"] = tracks_tick_df[
        "tick_global3d_coco13"
    ].apply(lambda x: np.nan_to_num(x, nan=-1))

    tracks_tick_df["tick_poem"] = tracks_tick_df["tick_poem"].apply(
        lambda x: np.nan_to_num(x, nan=-1)
    )

    movelets = tracks_tick_df[
        [
            "video_id",
            "track_id",
            "tick",
            "tick_start_frame",
            "tick_end_frame",
            "pose_idx",
            "prev_tick_norm",
            "tick_norm",
            "movelet_vector",
            "movement",
            "movement_3d",
            "tick_poem",
        ]
    ].values

    logging.info(f"Loading {len(movelets)} movelets into DB.")

    await db.add_video_movelets(movelets)

    logging.info("Computing cumulative movement per frame.")

    cumulative_movement_per_frame = {0: 0}
    cumulative_movement_per_frame_3d = {0: 0}

    max_movement = 0
    max_movement_3d = 0

    for frame in range(1, video_metadata["frame_count"]):
        active_ticks_df = tracks_tick_df[
            (tracks_tick_df["tick_start_frame"] <= frame)
            & (tracks_tick_df["tick_end_frame"] >= frame)
        ].copy()
        if len(active_ticks_df) == 0:
            cumulative_movement_per_frame[frame] = 0.0
            cumulative_movement_per_frame_3d[frame] = 0.0
        else:
            active_ticks_df["tick_frames_duration"] = (
                active_ticks_df["tick_end_frame"] - active_ticks_df["tick_start_frame"]
            )
            # XXX Not sure why it's necessary to do it this way. This should work:
            # active_ticks_df["motion_per_frame"] = np.where(
            #     active_ticks_df["tick_frames_duration"] <= 0,
            #     active_ticks_df["movement"] / active_ticks_df["tick_frames_duration"],
            #     0,
            # )
            # (according to my feeble brain) but it doesn't.

            active_ticks_df["motion_per_frame"] = np.where(
                active_ticks_df["tick_frames_duration"] <= 0,
                0,
                active_ticks_df["movement"],
            ) / np.where(
                active_ticks_df["tick_frames_duration"] <= 0,
                1,
                active_ticks_df["tick_frames_duration"],
            )
            movement = active_ticks_df["motion_per_frame"].sum()

            active_ticks_df["motion_per_frame_3d"] = np.where(
                active_ticks_df["tick_frames_duration"] <= 0,
                0,
                active_ticks_df["movement_3d"],
            ) / np.where(
                active_ticks_df["tick_frames_duration"] <= 0,
                1,
                active_ticks_df["tick_frames_duration"],
            )
            movement_3d = active_ticks_df["motion_per_frame_3d"].sum()

            if np.isnan(movement):
                cumulative_movement_per_frame[frame] = 0.0
            else:
                max_movement = max(max_movement, movement)
                cumulative_movement_per_frame[frame] = movement

            if np.isnan(movement_3d):
                cumulative_movement_per_frame_3d[frame] = 0.0
            else:
                max_movement_3d = max(max_movement_3d, movement_3d)
                cumulative_movement_per_frame_3d[frame] = movement_3d

    logging.info("Adding cumulative movement per frame to DB.")

    await db.add_frame_movement(
        video_id,
        max_movement,
        cumulative_movement_per_frame,
        max_movement_3d,
        cumulative_movement_per_frame_3d,
    )


if __name__ == "__main__":
    asyncio.run(main())
