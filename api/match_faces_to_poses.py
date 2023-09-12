#!/usr/bin/env python3

"""CLI to add face detection data to OpenPifPaf pose data for a video in the db."""

import argparse
import asyncio
import logging
from pathlib import Path

import numpy as np
from rich.logging import RichHandler

from mime_db import MimeDb


def unflatten_pose_data(keypoints):
    return np.array_split(keypoints, len(keypoints) / 3)


def extract_trustworthy_coords(keypoints):
    unflattened_pose = unflatten_pose_data(keypoints)
    trustworthy_coords = np.array(
        [
            [coords[0], coords[1]] if coords[2] != 0 else [np.NaN, np.NaN]
            for coords in unflattened_pose
        ]
    )
    return trustworthy_coords


def box_to_frame(bbox):
    return [bbox[0], bbox[0] + bbox[2], bbox[1], bbox[1] + bbox[3]]


def get_bbox_overlap(box1, box2):
    frame1 = box_to_frame(box1)
    frame2 = box_to_frame(box2)
    h_overlap = min(frame1[1], frame2[1]) - max(frame1[0], frame2[0])
    v_overlap = min(frame1[3], frame2[3]) - max(frame1[2], frame2[2])
    if h_overlap >= 0 and v_overlap >= 0:
        return h_overlap * v_overlap
    return 0


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

    # This should really just be the name of the video, since its pose data
    # should already be in the DB by the time this is run
    video_name = Path(args.video_name)

    # Connect to the database
    db = await MimeDb.create()

    # Get video metadata
    video_name = video_name.name
    video_id = await db.get_video_id(video_name)
    video_id = video_id[0]["id"]

    logging.info("Matching tracked poses to faces detected in video")

    track_frames = await db.get_track_frames(video_id)

    for track_frame in track_frames:
        logging.info(f"matching tracked poses to faces in frame {track_frame['frame']}")

        frame_faces = await db.get_frame_faces(video_id, track_frame["frame"])
        frame_poses = await db.get_frame_data(video_id, track_frame["frame"])

        for pose in frame_poses:
            if pose["track_id"] == 0:
                continue
            pose_head = extract_trustworthy_coords(pose["keypoints"])[:5, :]
            head_bbox = [
                np.nanmin(pose_head[:, 0]),
                np.nanmin(pose_head[:, 1]),
                np.nanmax(pose_head[:, 0]) - np.nanmin(pose_head[:, 0]),
                np.nanmax(pose_head[:, 1]) - np.nanmin(pose_head[:, 1]),
            ]
            if np.isnan(head_bbox).any():
                continue

            best_match = None
            best_overlap = 0
            for f, face in enumerate(frame_faces):
                bbox_overlap = get_bbox_overlap(face["bbox"], head_bbox)
                if bbox_overlap > best_overlap:
                    best_match = f
                    best_overlap = bbox_overlap

            if best_match is not None and best_overlap > 0:
                await db.assign_pose_face(
                    video_id,
                    track_frame["frame"],
                    pose["pose_idx"],
                    frame_faces[best_match]["bbox"],
                    frame_faces[best_match]["confidence"],
                    frame_faces[best_match]["landmarks"],
                    frame_faces[best_match]["embedding"],
                )
                logging.info(
                    f"matched face {frame_faces[best_match]['bbox']} to pose {pose['pose_idx']}, track {pose['track_id']} with head bbox {head_bbox}"
                )


if __name__ == "__main__":
    asyncio.run(main())
