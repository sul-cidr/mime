#!/usr/bin/env python3

"""CLI to add tracking data to OpenPifPaf pose data for a video in the db."""

import argparse
import asyncio
import logging
from pathlib import Path

import lib.pose_tracker as pose_tracker
from mime_db import MimeDb
from rich.logging import RichHandler


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

    pose_data = await db.get_pose_data_from_video(video_id)

    track_data = pose_tracker.track_poses(
        pose_data,
        video_metadata["fps"],
        video_metadata["width"],
        video_metadata["height"],
    )

    await db.add_video_tracks(video_id, track_data)


if __name__ == "__main__":
    asyncio.run(main())