#!/usr/bin/env python3

"""CLI to run face detection on a video file and write the output to a JSON file."""

import argparse
import asyncio
import logging
import pickle
from pathlib import Path

from rich.logging import RichHandler

from mime_db import MimeDb

SHOT_DETECT_THRESHOLD = 0.5


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
        help="Overwrite existing file",
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
    # should already be in the DB by the time this is run
    video_path = Path(args.video_path)
    input_path = f"{video_path}.shots.TransNetV2.pkl"

    single_frame_probs, all_frames_probs = pickle.load(open(input_path, "rb"))

    db = await MimeDb.create()

    # Get video metadata
    video_name = video_path.name
    video_id = await db.get_video_id(video_name)
    video_data = await db.get_video_by_id(video_id)
    video_frame_count = video_data["frame_count"]

    if len(all_frames_probs) != video_frame_count:
        logging.warning(
            "Video frame count in DB doesn't match count from shot detection"
        )

    frames_to_load = []
    BATCH_SIZE = 1000

    for i, frame_prob in enumerate(all_frames_probs):
        frames_to_load.append(
            [
                i,
                single_frame_probs[i],
                frame_prob,
                bool(frame_prob > SHOT_DETECT_THRESHOLD),
            ]
        )
        if len(frames_to_load) >= BATCH_SIZE or i == len(all_frames_probs) - 1:
            await db.add_shot_boundaries(video_id, frames_to_load)
            frames_to_load = []


if __name__ == "__main__":
    asyncio.run(main())
