#!/usr/bin/env python3

"""CLI to cache individual frames from a video as jpeg files."""

import argparse
import asyncio
import logging
import os
from pathlib import Path

import imageio.v3 as iio
from rich.logging import RichHandler

from mime_db import MimeDb


async def main() -> None:
    """Command-line entry-point."""

    parser = argparse.ArgumentParser(description="Description: {}".format(__doc__))

    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        default=False,
        help="Overwrite existing images at target path",
    )

    parser.add_argument("--video-name", action="store")
    parser.add_argument("--video-uuid", action="store")

    args = parser.parse_args()

    logging.basicConfig(
        level=(os.getenv("LOG_LEVEL") or "INFO").upper(),
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    if args.video_name and args.video_uuid:
        raise SystemExit("Error: cannot supply both --video-path and --video-uuid")

    # Create database
    logging.info("Initializing DB...")
    db = await MimeDb.create()

    if args.video_name:
        video_path = video_path = Path("/videos") / args.video_name
        assert video_path.exists(), f"'{video_path}' does not exist"
        video_record = await db.get_video_by_name(video_path.name)
        video_uuid = video_record.get("id", None)
        assert video_uuid is not None, f"'{video_uuid}' does not exist"

    elif args.video_uuid:
        video_uuid = args.video_uuid
        video_record = await db.get_video_by_id(video_uuid)
        video_name = video_record.get("video_name", None)
        assert video_uuid is not None, f"'{video_uuid}' does not exist"
        video_path = Path("/videos") / video_name
        assert video_path.exists(), f"'{video_path}' does not exist"

    else:
        raise SystemExit("Error: must supply either --video-path or --video-uuid")

    frame_count = video_record["frame_count"]

    logging.info(f"Video path: {video_path}")
    logging.info(f"Video UUID: {video_uuid}")
    logging.info(f"Frame Count: {frame_count}")

    Path(f"/static/{video_uuid}/frames").mkdir(parents=True, exist_ok=True)

    for i in range(frame_count):
        img = iio.imread(video_path, index=i, plugin="pyav")
        logging.info(f"Caching frame {i + 1} / {frame_count}")
        iio.imwrite(f"/static/{video_uuid}/frames/{i+1}.jpeg", img, extension=".jpeg")


if __name__ == "__main__":
    asyncio.run(main())
