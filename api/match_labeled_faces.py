#!/usr/bin/env python3

"""CLI to cluster detected faces for a video in the db."""

import argparse
import asyncio
import json
import logging
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
from rich.logging import RichHandler
from scipy.spatial.distance import cosine

from mime_db import MimeDb

# DeepFace and ArcFace resize/crop face images to 152x152 and 112x112 pixels,
# respectively, so an image upsized from smaller than 100xH px is not useful.
WIDTH_THRESHOLD = 100  # Desired face image width in pixels
FACE_FEATURES = 512  # Previously used DeepFace, which has 4096
UPSCALE = 5


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

    video_name = Path(args.video_name)

    # Connect to the database
    db = await MimeDb.create()

    # Get video metadata
    video_name = video_name.name
    video_id = await db.get_video_id(video_name)

    labeled_faces_path = Path(
        "/app", "labeled_face_images", video_name, "cluster_id_to_image.json"
    )
    if not os.path.isfile(labeled_faces_path):
        logging.error(
            f"No file with labeled face embeddings data found at {labeled_faces_path}"
        )
        return

    with open(labeled_faces_path, "r", encoding="utf-8") as json_input:
        labeled_faces_data = json.load(json_input)

    pose_faces = await db.get_poses_with_faces(video_id)

    pf_df = pd.DataFrame.from_records(pose_faces, columns=pose_faces[0].keys())

    logging.info(f"Total poses with faces: {len(pf_df)}")

    pf_df = pf_df[
        ((~np.isnan(pf_df["face_confidence"])) & (pf_df["face_confidence"] > 0.99))
    ].reset_index()

    logging.info(f"Poses with usable faces: {len(pf_df)}")

    logging.info("Looking for faces that are square to the camera")

    pf_df["face_landmarks_array"] = pf_df["face_landmarks"].apply(
        lambda f: np.array_split(np.array(f), len(f) / 2)
    )

    def get_angle(points):
        a = points[0]
        b = points[2]
        c = points[1]
        ang = math.degrees(
            math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(a[1] - b[1], a[0] - b[0])
        )
        return ang + 360 if ang < 0 else ang

    pf_df["nose_eyes_angle"] = pf_df["face_landmarks_array"].apply(get_angle)

    nose_angle_mean = pf_df["nose_eyes_angle"].mean()
    nose_angle_median = pf_df["nose_eyes_angle"].median()
    nose_angle_stdev = pf_df["nose_eyes_angle"].std()

    logging.info(f"mean nose angle {nose_angle_mean}")
    logging.info(f"median nose angle {nose_angle_median}")
    logging.info(f"nose angle stdev {nose_angle_stdev}")
    logging.info(f"max nose angle {pf_df['nose_eyes_angle'].max()}")
    logging.info(f"min nose angle {pf_df['nose_eyes_angle'].min()}")

    # pf_df["face_landmarks_aspect_ratio"] = pf_df["face_landmarks_array"].apply(
    #     lambda f: 0
    #     if (np.max(np.array(f)[:, 1]) - np.min(np.array(f)[:, 1])) == 0
    #     else (np.max(np.array(f)[:, 0]) - np.min(np.array(f)[:, 0]))
    #     / (np.max(np.array(f)[:, 1] - np.min(np.array(f)[:, 1])))
    # )

    # face_aspect_ratio_mean = pf_df["face_landmarks_aspect_ratio"].mean()
    # face_aspect_ratio_stdev = pf_df["face_landmarks_aspect_ratio"].std()

    # logging.info(f"mean face aspect ratio {face_aspect_ratio_mean}")
    # logging.info(f"face aspect ratio stdev {face_aspect_ratio_stdev}")

    # pf_df["aspect_ratio_dev"] = pf_df["face_landmarks_aspect_ratio"].apply(
    #     lambda f: abs(f - face_aspect_ratio_mean)
    # )

    # metric should be between 0 and 1, lower is better
    pf_df["nose_eyes_metric"] = pf_df["nose_eyes_angle"].apply(
        lambda f: 1
        if f < nose_angle_mean or f > nose_angle_mean + (nose_angle_stdev / 2)
        else abs((f - nose_angle_mean) / nose_angle_mean)
    )

    # This selects a single face to represent each track
    rep_pf_df = pf_df.iloc[
        (
            pf_df.groupby(["track_id"])["nose_eyes_metric"].idxmin()
            # pf_df.groupby(["track_id"])["aspect_ratio_dev"].idxmin()
        )
    ]

    def find_top_match_for_face(match_data):
        match_array = np.array(match_data)
        sim_avg = np.mean(match_array[:, 1])
        sim_stdev = np.std(match_array[:, 1])
        max_sim = np.max(match_array[:, 1])
        if max_sim > (sim_avg + sim_stdev):
            return np.argmax(match_array[:, 1])
        return None

    track_to_label = []

    logging.info("Matching detected faces in video to labeled cast faces")

    for _, row in rep_pf_df.iterrows():
        if row["face_confidence"] < 0.99 or row["nose_eyes_metric"] == 1:
            continue
        match_data = []
        for label_index, image_item in enumerate(labeled_faces_data):
            image_file = list(image_item.keys())[0]
            # image_label = image_file.split(".")[:-1]
            this_embedding = image_item[image_file]["embedding"]
            sim = 1 - cosine(row["face_embedding"], this_embedding)
            match_data.append([label_index, sim])
        best_match = find_top_match_for_face(match_data)
        if best_match is not None:
            track_to_label.append([video_id, best_match, int(row["track_id"])])

        if len(track_to_label) % 1000 == 0:
            logging.info("assigning 1000 face-to-track labels")
            await db.assign_face_clusters_by_track(track_to_label)
            track_to_label = []

    logging.info("assigning the remaining face-to-track labels")
    await db.assign_face_clusters_by_track(track_to_label)


if __name__ == "__main__":
    asyncio.run(main())
