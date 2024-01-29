#!/usr/bin/env python3

"""CLI to load POEM viewpoint-invariant ouput embeddings into the DB for a video."""

import argparse
import asyncio
import csv
import logging
import os

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

    video_name = args.video_name

    # Connect to the database
    db = await MimeDb.create()

    if not os.path.isdir(f"poem_files/{video_name}"):
        logging.error(f"No source folder for POEM input, should be at /api/poem_files/{video_name}")
        return

    # Output file from Pr_VIPE code
    poem_file = open(f"poem_files/{video_name}/unnormalized_embeddings.csv", "r", newline='', encoding="utf-8")

    # This file provides a key to the input, matching lines in the Pr_VIPE input
    # file to specific poses from the DB
    poses_file = open(f"poem_files/{video_name}/{video_name}.poses.csv", "r", newline='', encoding="utf-8")

    posesreader = csv.DictReader(poses_file)

    poem_embeddings_data = []

    for pose in posesreader:
        poem_line = poem_file.readline().strip().split(",")
        poem_coords = [float(c) for c in poem_line]
        poem_embeddings_data.append([pose["video_id"], int(pose["frame"]), int(pose["pose_idx"]), poem_coords])

    poem_file.close()
    poses_file.close()

    await db.assign_poem_embeddings(poem_embeddings_data)

if __name__ == "__main__":
    asyncio.run(main())