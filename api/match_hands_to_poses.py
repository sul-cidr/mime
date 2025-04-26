#!/usr/bin/env python3

"""CLI to add hand detection data to pose data for a video in the db."""

import argparse
import asyncio
import logging
from pathlib import Path

import jsonlines
import numpy as np
from rich.logging import RichHandler

from mime_db import MimeDb

BATCH_SIZE = 1000


def unflatten_3d(kpts_3d):
    return np.array_split(kpts_3d, len(kpts_3d) / 3)


def get_hand_center(hand_3d):
    # Hand keypoints are already unflattened in the JSON file
    xmin = min(hand_3d[:,0])
    xmax = max(hand_3d[:,0])
    ymin = min(hand_3d[:,1])
    ymax = max(hand_3d[:,1])
    zmin = min(hand_3d[:,2])
    zmax = max(hand_3d[:,2])

    return np.array([abs(xmax - xmin)/2, abs(ymax - ymin)/2, abs(zmax - zmin)/2])


async def match_hands_in_frames(video_id, hands_to_match, min_frameno, max_frameno, db):
    logging.info(
        f"Running match_hands_in_frames with start frame {min_frameno} end {max_frameno}"
    )

    matches_to_assign = []

    frame_poses = await db.get_frame_data_range(video_id, min_frameno, max_frameno)

    poses_by_frame = {}
    for pose in frame_poses:
        if pose["frame"] in poses_by_frame:
            poses_by_frame[pose["frame"]].append(pose)
        else:
            poses_by_frame[pose["frame"]] = [pose]

    for frameno in hands_to_match:
        if frameno not in poses_by_frame:
            continue
        frame_hands = hands_to_match[frameno]
        frame_poses = poses_by_frame[frameno]

        # There are usually more poses than hands, so we'll start with hands

        for h, hand in enumerate(frame_hands):
            hand_center = get_hand_center(np.array(hand["kpts_3d"]))

            closest_dist = 0
            best_pose_match = None

            is_right = hand["right"] == 1

            # Match each left/right hand to the closest left/right wrist
            if is_right is True:
                target_wrist = unflatten_3d(pose["keypoints3d"])[6]
            else:
                target_wrist = unflatten_3d(pose["keypoints3d"])[7]

            for pose in frame_poses:
                # Necessary?
                if pose["track_id"] == 0:
                    continue

                wrist_hand_dist = np.linalg.norm(target_wrist - hand_center)
                if closest_dist != 0 and closest_dist < wrist_hand_dist:
                    continue
                else:
                    closest_dist = wrist_hand_dist
                    best_pose_match = pose["pose_idx"]


            if best_pose_match is not None:

                if "confidence" in hand:
                    confidence = hand["confidence"]
                else:
                    confidence = 1

                # Flatten arrays of coordinates into flat vectors for DB ingest
                kpts_2d = [
                    coord for pair in hand["kpts_2d"] for coord in pair
                ]
                kpts_3d = [
                    coord for triplet in hand["kpts_3d"] for coord in triplet
                ]
                global_orient = [
                    coord for triplet in hand["global_orient"] for coord in triplet
                ]

                matches_to_assign.append(
                    [
                        video_id,
                        frameno,
                        best_pose_match,
                        hand["personid"],
                        hand["bbox"],
                        is_right,
                        confidence,
                        hand["pred_cam"],
                        hand["cam_t"],
                        kpts_2d,
                        kpts_3d,
                        global_orient,
                        pose["track_id"],
                    ]
                )

    if len(matches_to_assign) > 0:
        await db.add_pose_hands(matches_to_assign)


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

    hands_file = Path(f"{args.video_name}.hands.WiLoR.jsonl")

    video_name = Path(args.video_name)

    # Connect to the database
    db = await MimeDb.create()

    # Get video metadata
    video_name = video_name.name
    video_id = await db.get_video_id(video_name)

    # Only consider frames with tracked poses in them
    track_frame_records = await db.get_track_frames(video_id)

    track_frame_ids = {frame_record["frame"] for frame_record in track_frame_records}

    hands_to_match = {}
    min_frameno = None
    max_frameno = None

    logging.info("Matching tracked poses to hands detected in video")

    with jsonlines.open(hands_file) as reader:
        for hand in reader:
            if (
                ("confidence" in hand and hand["confidence"] == 0)
                or hand["frame"] not in track_frame_ids
            ):
                continue

            if hand["frame"] in hands_to_match:
                hands_to_match[hand["frame"]].append(hand)
            else:
                hands_to_match[hand["frame"]] = [hand]

            if min_frameno is None:
                min_frameno = hand["frame"]
            else:
                min_frameno = min(min_frameno, hand["frame"])

            if max_frameno is None:
                max_frameno = hand["frame"]
            else:
                max_frameno = max(max_frameno, hand["frame"])

            if len(hands_to_match) >= BATCH_SIZE:
                await match_hands_in_frames(
                    video_id, hands_to_match, min_frameno, max_frameno, db
                )
                hands_to_match = {}
                min_frameno = None
                max_frameno = None

        if len(hands_to_match) > 0:
            await match_hands_in_frames(
                video_id, hands_to_match, min_frameno, max_frameno, db
            )


if __name__ == "__main__":
    asyncio.run(main())
