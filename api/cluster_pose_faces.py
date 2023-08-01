#!/usr/bin/env python3

"""CLI to average and cluster detected faces from OpenPifPaf tracked poses for a video."""

import argparse
import asyncio
import logging
from pathlib import Path

import imageio.v3 as iio
import numpy as np
import pandas as pd
from deepface.commons import distance as dst
from deepface.commons import functions, realtime
from mime_db import MimeDb
from rich.logging import RichHandler

DISTANCE_THRESHOLD = 0.13
SIZE_THRESHOLD = 40  # pixels of width


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
        help="Re-cluster faces",
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

    # Connect to the database
    db = await MimeDb.create()

    # Get video metadata
    video_name = video_path.name
    video_id = await db.get_video_id(video_name)
    video_id = video_id[0]["id"]

    video_poses = await db.get_pose_data_from_video(video_id)

    poses_df = pd.DataFrame.from_records(video_poses, columns=video_poses[0].keys())

    # This assumes that every track only follows one person, which is correct
    # in theory (but in practice ...)
    logging.info("Averaging face vectors for tracks")

    def average_face_embeddings(embeddings):
        # Not sure why all these conversions are necessary...
        embeddings = np.array([embed for embed in embeddings])
        # Need at least 5 frames/poses to consider this a reliable face
        if embeddings.shape[0] < 5:
            avg_embed = None
        else:
            avg_embed = np.mean(embeddings, axis=0)
        return [avg_embed] * embeddings.shape[0]

    def get_face_area(p):
        if p["face_bbox"] is None:
            return 0
        return p["face_bbox"][2] * p["face_bbox"][3]

    similarity_threshold = dst.findThreshold("DeepFace", "cosine")
    logging.info(f"Similarity threshold for DeepFace+cosine is {similarity_threshold}")

    # We can use the largest face image as a thumbnail (if desired)
    poses_df["face_area"] = poses_df[~poses_df["face_bbox"].isnull()].apply(
        get_face_area, axis=1
    )

    poses_df["face_avg"] = (
        poses_df[~poses_df["face_bbox"].isnull()]
        .groupby(["track_id"])["face_embedding"]
        .transform(average_face_embeddings)
    )

    rep_poses_df = poses_df.iloc[
        (
            poses_df[~poses_df["face_avg"].isnull()]
            .groupby(["track_id"])["face_area"]
            .idxmax()
        )
    ]

    print(rep_poses_df[["track_id", "frame", "face_bbox", "face_area", "face_avg"]])

    rep_poses = rep_poses_df.to_dict("records")

    # Copied from deepface (not sure why it doesn't just use scipy though)
    def cosine_distance(source_representation, test_representation):
        a = np.matmul(np.transpose(source_representation), test_representation)
        b = np.sum(np.multiply(source_representation, source_representation))
        c = np.sum(np.multiply(test_representation, test_representation))
        return 1 - (a / (np.sqrt(b) * np.sqrt(c)))

    for i, first_pose in enumerate(rep_poses):
        for j, second_pose in enumerate(rep_poses):
            if i >= j:
                continue
            if (
                first_pose["face_bbox"][2] < SIZE_THRESHOLD
                or second_pose["face_bbox"][2] < SIZE_THRESHOLD
            ):
                continue
            # dist = cosine_distance(first_pose["face_avg"], second_pose["face_avg"])
            dist = cosine_distance(
                first_pose["face_embedding"], second_pose["face_embedding"]
            )
            # if dist <= similarity_threshold:
            if dist <= DISTANCE_THRESHOLD:
                print(i, j, dist)
                x, y, w, h = [round(coord) for coord in first_pose["face_bbox"]]
                video_file = f"/videos/{video_name}"
                img = iio.imread(
                    video_file, index=first_pose["frame"] - 1, plugin="pyav"
                )
                img_region = img[y : y + h, x : x + w]
                iio.imwrite(f"{i}_{j}_1.jpg", img_region, extension=".jpeg")
                x, y, w, h = [round(coord) for coord in second_pose["face_bbox"]]
                video_file = f"/videos/{video_name}"
                img = iio.imread(
                    video_file, index=second_pose["frame"] - 1, plugin="pyav"
                )
                img_region = img[y : y + h, x : x + w]
                iio.imwrite(f"{i}_{j}_2.jpg", img_region, extension=".jpeg")


if __name__ == "__main__":
    asyncio.run(main())
