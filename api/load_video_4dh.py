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

import lib.pose_utils as pose_utils
from mime_db import MimeDb


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


def normalize_pose_data(pose, key="keypoints"):
    normalized_coords = pose_utils.extract_trustworthy_coords(
        pose_utils.shift_normalize_rescale_pose_coords(pose, key)
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
        "vector(26)",
        video_id,
        lambda pose: tuple(
            np.nan_to_num(normalize_pose_data(pose, "keypoints"), nan=-1).tolist()
        ),
    )

    # Normalize 3D pose data and annotate database records
    logging.info("Normalizing 3D pose data, and annotating db records...")
    await db.annotate_pose(
        "global3d_coco13",
        "vector(39)",
        video_id,
        lambda pose: tuple(
            pose_utils.merge_coords(
                np.array(pose["global3d_phalp"]).reshape(-1, 3),
                pose_utils.phalp_to_coco_13,
                is_3d=True,
            )
            .flatten()
            .tolist()
        ),
    )

    # This is for when we want to merge the full 45-point PHALP set into a set of
    # normalized COCO points for pose similarity and clustering calculations
    # Normalize pose data and annotate database records
    # logging.info("Normalizing pose data, and annotating db records...")
    # await db.annotate_pose(
    #     "norm",
    #     "vector(34)",
    #     video_id,
    #     lambda pose: tuple(np.nan_to_num(normalize_pose_data({"keypoints": merge_phalp_coords(pose['keypoints'].reshape(-1, 2), phalp_to_coco).flatten()}), nan=-1).tolist()),
    #     pose_tbl="pose4dh"
    # )

    # We're not using this at present, either
    # await db.annotate_pose(
    #     "norm4dh",
    #     "vector(90)",
    #     video_id,
    #     lambda pose: tuple(np.nan_to_num(normalize_pose_data(pose, "keypoints4dh"), nan=-1).tolist()),
    # )


if __name__ == "__main__":
    asyncio.run(main())
