#!/usr/bin/env python3

"""CLI to load hand detection data from a JSON lines file for a video in the db."""

"""NOTE: This script has never been tested and is only provided as a skeleton
in case the recommended path of using api/match_hands_to_poses.py provdes
undesirable for some reason."""

import argparse
import asyncio
import logging
from pathlib import Path

import jsonlines
from rich.logging import RichHandler

from mime_db import MimeDb

BATCH_SIZE = 1000  # How many hands to load into DB at one time


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
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite data in the DB hand table",
    )

    parser.add_argument(
        "--json-path",
        action="store",
        required=True,
        help="The filename should be [video_filename].hands.[method].jsonl",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    # This should really just be the name of the video, since its pose data
    # should already be in the DB by the time this is run
    input_path = Path(args.json_path)

    # Connect to the database
    db = await MimeDb.create()

    # Get video metadata
    json_file = input_path.name

    video_name = json_file.split(".hands.")[0] #.replace(".hands.jsonl", "")

    video_id = await db.get_video_id(video_name)
    video_id = video_id[0]["id"]

    logging.info("Loading hand detection results from JSON file into the DB")

    with jsonlines.open(input_path) as reader:
        hands_to_add = []
        for hand in reader:
            if len(hands_to_add) >= BATCH_SIZE:
                await db.add_video_hands(video_id, hands_to_add)
                hands_to_add = []

            is_right = hand["right"] == 1

            if "confidence" in hand:
                confidence = hand["confidence"]
            else:
                confidence = 1
            # Don't bother
            #if hand["confidence"] == 0:
            #    continue
            kpts_2d = [
                coord for pair in hand["kpts_2d"] for coord in pair
            ]
            kpts_3d = [
                coord for triplet in hand["kpts_3d"] for coord in triplet
            ]
            global_orient = [
                coord for triplet in hand["global_orient"] for coord in triplet
            ]

            hands_to_add.append(
                [
                    hand["frame"],
                    None,
                    hand["personid"],
                    hand["bbox"],
                    is_right,
                    confidence,
                    hand["pred_cam"],
                    hand["cam_t"],
                    kpts_2d,
                    kpts_3d,
                    global_orient,
                ]
            )
        if len(hands_to_add) > 0:
            await db.add_video_hands(video_id, hands_to_add)


if __name__ == "__main__":
    asyncio.run(main())
