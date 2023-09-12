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
    video_id = video_id[0]["id"]

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

    def avg_norm_data(norms):
        norms_with_nans = [np.where(norm == -1, np.nan, norm) for norm in norms]
        return [np.nanmean(norms_with_nans, axis=0)] * len(norms)

    tracks_df["tick_norm"] = tracks_df.groupby(["track_id", "tick"])["norm"].transform(
        avg_norm_data
    )

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
        lambda x: [np.nan] * 34 if type(x) == float else x
    )

    def compute_motion_vector(timediff, last_norm, norm):
        if np.isnan(timediff) or timediff == 0 or type(last_norm) == float:
            return [np.nan] * 34
        normdiff = []
        for i in range(0, 34, 2):
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
        if np.isnan(timediff) or timediff == 0 or type(last_norm) == float:
            return np.nan  # usually this is the first frame in the movelet
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

    tracks_tick_df["movelet_vector"] = tracks_tick_df["movelet_vector"].apply(
        lambda x: np.nan_to_num(x, nan=-1)
    )

    tracks_tick_df["prev_tick_norm"] = tracks_tick_df["prev_tick_norm"].apply(
        lambda x: np.nan_to_num(x, nan=-1)
    )

    tracks_tick_df["tick_norm"] = tracks_tick_df["tick_norm"].apply(
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
            "tick_start_timecode",
            "tick_end_timecode",
            "prev_tick_norm",
            "tick_norm",
            "movelet_vector",
            "movement",
        ]
    ].values

    logging.info(f"Loading {len(movelets)} movelets into DB.")

    await db.add_video_movelets(movelets)

    # await db.annotate_movelet(
    #     "normed_motion",
    #     "vector(68)",
    #     video_id,
    #     lambda movelet: tuple(np.nan_to_num(), nan=-1).tolist()),
    # )

    # unique_track_ids = await db.get_unique_track_ids_from_video(video_id)

    # # Might be preferable to work with these in a dataframe...
    # for track_id in unique_track_ids:
    #     last_window_means = None
    #     # For every 1/6 sec window of track data,
    #     # average the positions
    #     # Then compare adjacent 1/6 windows to get motion vectors for each kpt
    #     window_start_time = None
    #     last_frame_time = None
    #     window_poses = []
    #     for pose in track_data:
    #         if pose["track_id"] != track_id:
    #             continue
    #         frame_time = float(video_metadata["fps"]) * pose["frame"]
    #         if window_start_time is None:
    #             window_start_time = frame_time
    #             last_frame_time = frame_time
    #             window_poses = [pose["norm"]]
    #         else:
    #             if frame_time - window_start_time > TICK_INTERVAL:
    #                 window_obs = np.array(window_poses)
    #                 window_obs = np.where(window_obs == -1, np.nan, window_obs)
    #                 window_means = np.nanmean(window_obs, axis=0)

    #             else:
    #                 window_poses.append(pose["norm"])

    # Once we have the motion data for a pose frame, add it as an annotation
    #     await db.annotate_pose(
    #     "normed_motion",
    #     "vector(34)",
    #     video_id,
    #     lambda pose: tuple(np.nan_to_num(normalize_pose_data(pose), nan=-1).tolist()),
    # )


if __name__ == "__main__":
    asyncio.run(main())
