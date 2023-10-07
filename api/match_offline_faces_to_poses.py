#!/usr/bin/env python3

"""CLI to add face detection data to OpenPifPaf pose data for a video in the db."""

import argparse
import asyncio
import logging
from pathlib import Path

import jsonlines
import numpy as np
from mime_db import MimeDb
from rich.logging import RichHandler

BATCH_SIZE = 1000


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

    parser.add_argument(
        "--faces-file",
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

    video_name = Path(args.video_name)

    # Connect to the database
    db = await MimeDb.create()

    # Get video metadata
    video_name = video_name.name
    video_id = await db.get_video_id(video_name)

    track_frame_records = await db.get_track_frames(video_id)

    track_frame_ids = {frame_record["frame"] for frame_record in track_frame_records}

    faces_to_match = {}
    min_frameno = None
    max_frameno = None

    async def match_faces_in_frames(faces_to_match, min_frameno, max_frameno):
        logging.info(
            f"Running match_faces_in_frames with start frame {min_frameno} end {max_frameno}"
        )

        matches_to_assign = []

        frame_poses = await db.get_frame_data_range(video_id, min_frameno, max_frameno)

        poses_by_frame = {}
        for pose in frame_poses:
            if pose["frame"] in poses_by_frame:
                poses_by_frame[pose["frame"]].append(pose)
            else:
                poses_by_frame[pose["frame"]] = [pose]

        for frameno in faces_to_match:
            if frameno not in poses_by_frame:
                continue
            frame_faces = faces_to_match[frameno]
            frame_poses = poses_by_frame[frameno]

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
                    landmarks_vector = [
                        coord
                        for pair in frame_faces[best_match]["landmarks"].values()
                        for coord in pair
                    ]

                    embedding = frame_faces[best_match]["embedding"]
                    if len(frame_faces[best_match]["embedding"]) < 4096:
                        embedding.extend(
                            [0] * (4096 - len(frame_faces[best_match]["embedding"]))
                        )

                    matches_to_assign.append(
                        [
                            video_id,
                            frameno,
                            pose["pose_idx"],
                            frame_faces[best_match]["bbox"],
                            frame_faces[best_match]["confidence"],
                            landmarks_vector,
                            embedding,
                            pose["track_id"],
                        ]
                    )

        if len(matches_to_assign) > 0:
            await db.add_pose_faces(matches_to_assign)

    logging.info("Matching tracked poses to faces detected in video")

    with jsonlines.open(args.faces_file) as reader:
        for face in reader:
            if (
                face["confidence"] == 0
                or not face["landmarks"]
                or face["frame"] not in track_frame_ids
            ):
                continue

            if face["frame"] in faces_to_match:
                faces_to_match[face["frame"]].append(face)
            else:
                faces_to_match[face["frame"]] = [face]

            if min_frameno is None:
                min_frameno = face["frame"]
            else:
                min_frameno = min(min_frameno, face["frame"])

            if max_frameno is None:
                max_frameno = face["frame"]
            else:
                max_frameno = max(max_frameno, face["frame"])

            if len(faces_to_match) >= BATCH_SIZE:
                await match_faces_in_frames(faces_to_match, min_frameno, max_frameno)
                faces_to_match = {}
                min_frameno = None
                max_frameno = None

        if len(faces_to_match) > 0:
            await match_faces_in_frames(faces_to_match, min_frameno, max_frameno)


if __name__ == "__main__":
    asyncio.run(main())
