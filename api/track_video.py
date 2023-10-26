#!/usr/bin/env python3

"""CLI to add tracking data to OpenPifPaf pose data for a video in the db."""

import argparse
import asyncio
import logging
from pathlib import Path

from rich.logging import RichHandler

import lib.pose_tracker as pose_tracker
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

    pose_data = await db.get_pose_data_from_video(video_id)

    shot_boundary_frames = await db.get_video_shot_boundaries(video_id)

    track_data = pose_tracker.track_poses(
        pose_data,
        video_metadata["fps"],
        video_metadata["width"],
        video_metadata["height"],
        shot_boundary_frames,
    )

    logging.info("Adding pose track data to the DB")
    await db.add_video_tracks(video_id, track_data)


if __name__ == "__main__":
    asyncio.run(main())
