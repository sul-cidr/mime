#!/usr/bin/env python3

"""CLI to load data from a video and corresponding PHALP (4D Humans) output into the db."""

import argparse
import asyncio
import logging
import os
from pathlib import Path

import cv2
import numpy as np
from rich.logging import RichHandler

import lib.pose_normalization as pose_normalization
from mime_db import MimeDb

phalp_to_reduced = [[0, 15, 16, 17, 18, 38, 43], [1, 37, 40], [2, 33], [3, 32], [4, 31], [5, 34], [6, 35], [7, 36], [8, 39], [9], [10, 26], [11, 24], [12], [13, 29], [14, 21], [19, 20], [21], [22, 23], [25], [27], [28], [30], [36], [41], [42], [44]]

phalp_to_coco = [[0], [16], [15], [18], [17], [5, 34], [2, 33], [6, 35], [3, 32], [7, 36], [4, 31], [28], [27], [13, 29], [10, 26], [14, 30], [11, 25]]

def merge_phalp_coords(all_coords, phalp_to_merge):
    new_coords = []
    for to_merge in phalp_to_merge:
        x_avg = sum([all_coords[i][0] for i in to_merge]) / len(to_merge)
        y_avg = sum([all_coords[i][1] for i in to_merge]) / len(to_merge)
        new_coords.append([x_avg, y_avg, 1.0]) # Add a bogus confidence value because the other code expects it

    return np.array(new_coords)


def get_video_metadata(video_file):
    # TODO: rewrite this without OpenCV?
    #  (currently this is the only time OpenCV is needed in this container --
    #   and it's a hefty dependency for just this..!)
    cap = cv2.VideoCapture(str(video_file))
    return {
        "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "fps": float(cap.get(cv2.CAP_PROP_FPS)),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }


def normalize_pose_data(pose, key='keypoints'):
    normalized_coords = pose_normalization.extract_trustworthy_coords(
        pose_normalization.shift_normalize_rescale_pose_coords(pose, key)
    )
    return normalized_coords


async def main() -> None:
    """Command-line entry-point."""

    parser = argparse.ArgumentParser(description="Description: {}".format(__doc__))

    parser.add_argument(
        "--drop",
        action="store_true",
        default=False,
        help="Drop (if existing) and recreate tables",
    )

    parser.add_argument("--video-path", action="store", required=True)
    parser.add_argument("--pkl-path", action="store")

    args = parser.parse_args()

    logging.basicConfig(
        level=(os.getenv("LOG_LEVEL") or "INFO").upper(),
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    video_path = Path(args.video_path)
    assert video_path.exists(), f"'{video_path}' does not exist"

    if args.pkl_path:
        pkl_path = Path(args.pkl_path)
    else:
        pkl_path = Path(f"{video_path}.phalp.pkl")
        logging.debug(f"--pkl-path not supplied, using '{pkl_path}'")

    assert pkl_path.exists(), f"'{pkl_path}' does not exist"

    # Create database
    logging.info("Initializing DB...")
    db = await MimeDb.create(drop=args.drop)

    # Get video metadata and add to database
    video_metadata = get_video_metadata(video_path)
    video_id = await db.add_video(video_path.name, video_metadata)

    logging.info("Loading pose data into DB")

    # Load pose data into database
    await db.load_4dh_predictions(video_id, pkl_path)

    # Normalize pose data and annotate database records
    logging.info("Normalizing pose data, and annotating db records...")
    await db.annotate_pose(
        "norm",
        "vector(34)",
        video_id,
        lambda pose: tuple(np.nan_to_num(normalize_pose_data(pose, "keypoints"), nan=-1).tolist()),
    )

    await db.annotate_pose(
        "norm4dh",
        "vector(90)",
        video_id,
        lambda pose: tuple(np.nan_to_num(normalize_pose_data(pose, "keypoints4dh"), nan=-1).tolist()),
    )


    # This is for when we want to merge the full 45-point PHALP set into a set of
    # normalized COCO points
    # Normalize pose data and annotate database records
    # logging.info("Normalizing pose data, and annotating db records...")
    # await db.annotate_pose(
    #     "norm",
    #     "vector(34)",
    #     video_id,
    #     lambda pose: tuple(np.nan_to_num(normalize_pose_data({"keypoints": merge_phalp_coords(pose['keypoints'].reshape(-1, 2), phalp_to_coco).flatten()}), nan=-1).tolist()),
    #     pose_tbl="pose4dh"
    # )

if __name__ == "__main__":
    asyncio.run(main())
