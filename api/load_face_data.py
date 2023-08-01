#!/usr/bin/env python3

"""CLI to load face detection data from a JSON lines file for a video in the db."""

import argparse
import asyncio
import logging
from pathlib import Path

import jsonlines
from mime_db import MimeDb
from rich.logging import RichHandler

BATCH_SIZE = 1000  # How many faces to load into DB at one time


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
        help="Overwrite data in the DB face table",
    )

    parser.add_argument(
        "--json-path",
        action="store",
        required=True,
        help="The filename should be [video_filename].faces.jsonl",
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

    video_name = json_file.replace(".faces.jsonl", "")

    video_id = await db.get_video_id(video_name)
    video_id = video_id[0]["id"]

    logging.info("Loading face detection results from JSON file into the DB")

    with jsonlines.open(input_path) as reader:
        faces_to_add = []
        for face in reader:
            if len(faces_to_add) >= BATCH_SIZE:
                await db.add_video_faces(video_id, faces_to_add)
                faces_to_add = []
            # Don't bother
            if face["confidence"] == 0 or not face["landmarks"]:
                continue
            landmarks_vector = [
                coord for pair in face["landmarks"].values() for coord in pair
            ]
            faces_to_add.append(
                [
                    face["frame"],
                    face["bbox"],
                    face["confidence"],
                    landmarks_vector,
                    face["embedding"],
                ]
            )
        if len(faces_to_add) > 0:
            await db.add_video_faces(video_id, faces_to_add)


if __name__ == "__main__":
    asyncio.run(main())
