#!/usr/bin/env python3

"""CLI to load action recognition data from LART output file into the db."""

import argparse
import asyncio
import logging
import os
from pathlib import Path

from rich.logging import RichHandler

from mime_db import MimeDb


async def main() -> None:
    """Command-line entry-point."""

    parser = argparse.ArgumentParser(description="Description: {}".format(__doc__))

    parser.add_argument("--pkl-path", action="store")
    parser.add_argument("--clear", action="store")

    args = parser.parse_args()

    logging.basicConfig(
        level=(os.getenv("LOG_LEVEL") or "INFO").upper(),
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    pkl_path = Path(args.pkl_path)

    assert pkl_path.exists(), f"'{pkl_path}' does not exist"

    # Connect to database
    logging.info("Initializing DB...")
    db = await MimeDb.create()

    pkl_file = pkl_path.name

    video_name = pkl_file.replace(".lart.pkl", "")

    video_id = await db.get_video_id(video_name)

    if args.clear and args.clear != "false":
        logging.info("Clearing previous action data for video")
        await db.clear_actions(video_id)

    logging.info("Loading action recognition data into DB")

    # Load pose data into database
    await db.load_lart_predictions(video_id, pkl_path)


if __name__ == "__main__":
    asyncio.run(main())
