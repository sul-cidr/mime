#!/usr/bin/env python3

"""CLI to load data from a video and corresponding OpenPifPaf output into the db."""

import argparse
import asyncio
import logging
import os
from pathlib import Path

from mime_db import MimeDb
from rich.logging import RichHandler


async def main() -> None:
    """Command-line entry-point."""

    parser = argparse.ArgumentParser(description="Description: {}".format(__doc__))

    parser.add_argument("--video-path", action="store", required=True)

    args = parser.parse_args()

    logging.basicConfig(
        level=(os.getenv("LOG_LEVEL") or "INFO").upper(),
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    video_path = Path(args.video_path)
    assert video_path.exists(), f"'{video_path}' does not exist"

    # Connect to the database
    db = await MimeDb.create()

    video_name = video_path.name
    video_id = await db.get_video_id(video_name)

    await db.remove_video(video_id)


if __name__ == "__main__":
    asyncio.run(main())
