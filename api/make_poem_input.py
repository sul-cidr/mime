#!/usr/bin/env python3

"""CLI to prepare input CSV(!) files for POEM viewpoint-invariant embeddings for a video's poses."""

import argparse
import asyncio
import csv
import logging
import os
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from mime_db import MimeDb
from rich.logging import RichHandler

CSV_HEADERS = [
"image/width",
"image/height",
"image/object/part/NOSE_TIP/center/x",
"image/object/part/NOSE_TIP/center/y",
"image/object/part/NOSE_TIP/score",
"image/object/part/LEFT_SHOULDER/center/x",
"image/object/part/LEFT_SHOULDER/center/y",
"image/object/part/LEFT_SHOULDER/score",
"image/object/part/RIGHT_SHOULDER/center/x",
"image/object/part/RIGHT_SHOULDER/center/y",
"image/object/part/RIGHT_SHOULDER/score",
"image/object/part/LEFT_ELBOW/center/x",
"image/object/part/LEFT_ELBOW/center/y",
"image/object/part/LEFT_ELBOW/score",
"image/object/part/RIGHT_ELBOW/center/x",
"image/object/part/RIGHT_ELBOW/center/y",
"image/object/part/RIGHT_ELBOW/score",
"image/object/part/LEFT_WRIST/center/x",
"image/object/part/LEFT_WRIST/center/y",
"image/object/part/LEFT_WRIST/score",
"image/object/part/RIGHT_WRIST/center/x",
"image/object/part/RIGHT_WRIST/center/y",
"image/object/part/RIGHT_WRIST/score",
"image/object/part/LEFT_HIP/center/x",
"image/object/part/LEFT_HIP/center/y",
"image/object/part/LEFT_HIP/score",
"image/object/part/RIGHT_HIP/center/x",
"image/object/part/RIGHT_HIP/center/y",
"image/object/part/RIGHT_HIP/score",
"image/object/part/LEFT_KNEE/center/x",
"image/object/part/LEFT_KNEE/center/y",
"image/object/part/LEFT_KNEE/score",
"image/object/part/RIGHT_KNEE/center/x",
"image/object/part/RIGHT_KNEE/center/y",
"image/object/part/RIGHT_KNEE/score",
"image/object/part/LEFT_ANKLE/center/x",
"image/object/part/LEFT_ANKLE/center/y",
"image/object/part/LEFT_ANKLE/score",
"image/object/part/RIGHT_ANKLE/center/x",
"image/object/part/RIGHT_ANKLE/center/y",
"image/object/part/RIGHT_ANKLE/score"
]


def get_video_metadata(video_file):
    cap = cv2.VideoCapture(str(video_file))
    return {
        "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "fps": float(cap.get(cv2.CAP_PROP_FPS)),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }


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
        "--video-path",
        action="store",
        required=True,
        help="The path to the video file (with extension)",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    video_path = Path(args.video_path)
    video_name = video_path.name

    video_metadata = get_video_metadata(video_path)

    # Connect to the database
    db = await MimeDb.create()

    # Get video ID
    video_id = await db.get_video_id(video_name)

    video_poses = await db.get_pose_data_from_video(video_id)

    if not os.path.isdir(f"poem_files/{video_name}"):
        os.makedirs(f"poem_files/{video_name}")

    # Input file to Pr_VIPE code
    poem_file = open(f"poem_files/{video_name}/{video_name}.csv", "w", newline='', encoding="utf-8")

    # This file provides a key to the input, matching lines in the Pr_VIPE input
    # file to specific poses from the DB
    poses_file = open(f"poem_files/{video_name}/{video_name}.poses.csv", "w", newline='', encoding="utf-8")

    poemwriter = csv.writer(poem_file)
    poemwriter.writerow(CSV_HEADERS)

    poseswriter = csv.writer(poses_file)
    poseswriter.writerow(["video_id", "frame", "pose_idx"])

    for pose in video_poses:
        posenorm = np.array(pose["norm"])
        posenorm = posenorm / 100
        pose_data = np.array([[posenorm[x], posenorm[x+1], 1] for x in range(0, len(posenorm), 2)]).flatten().tolist()
        rowdata = [video_metadata["width"]] + [video_metadata["height"]] + pose_data
        poemwriter.writerow(rowdata)

        poseswriter.writerow([video_id, pose["frame"], pose["pose_idx"]])

    poem_file.close()
    poses_file.close()

if __name__ == "__main__":
    asyncio.run(main())
