#!/usr/bin/env python3

"""CLI to cluster detected faces for a video in the db."""

import argparse
import asyncio
import logging
import os
from pathlib import Path

import cv2
import imageio.v3 as iio
import numpy as np
import pacmap
import pandas as pd
from PIL import Image
from rich.logging import RichHandler
from sklearn.cluster import KMeans

from mime_db import MimeDb

# DeepFace and ArcFace resize/crop face images to 152x152 and 112x112 pixels,
# respectively, so an image upsized from smaller than 100xH px is not useful.
WIDTH_THRESHOLD = 100  # Desired face image width in pixels
DEFAULT_CLUSTERS = 15  # Expected number of face clusters
FACE_FEATURES = 512  # For ArcFace, previously used DeepFace, which has 4096
UPSCALE = 5
FACE_SAMPLE_RATE = 2000  # Faces to skip when creating averages


# This averages the feature vectors of every frame of a given face/track.
# The resulting vector is of limited use, because a pose's face
# orientation can change a lot across a movement track, and pretty much
# all face feature extractors are sensitive to face orientation (pose).
# Also assumes that every track always follows the same person throughout
# its duration, which is correct in theory (but in practice not so much)
def average_face_embeddings(embeddings):
    # Not sure why all these conversions are necessary...
    embeddings = np.array(list(embeddings))
    # Need at least 5 frames/poses to consider this a reliable face
    if embeddings.shape[0] < 5:
        avg_embed = None
    else:
        avg_embed = np.mean(embeddings, axis=0)
    return [avg_embed] * embeddings.shape[0]


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
        "--n_clusters",
        action="store",
        required=False,
        default=DEFAULT_CLUSTERS,
        help="The expected number of face clusters in the recording",
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

    pose_faces = await db.get_poses_with_faces(video_id)

    # Keep the original set of pose faces for cluster timeline assignment
    all_pf_df = pd.DataFrame.from_records(pose_faces, columns=pose_faces[0].keys())

    pf_df = all_pf_df.copy()

    logging.info(f"Total poses with faces: {len(pf_df)}")

    pf_df = pf_df[
        ((~np.isnan(pf_df["face_confidence"])) & (pf_df["face_confidence"] > 0))
    ].reset_index()

    logging.info(f"Poses with usable faces: {len(pf_df)}")

    logging.info("Looking for faces that are square to the camera")
    pf_df["face_landmarks_array"] = pf_df["face_landmarks"].apply(
        lambda f: np.array_split(np.array(f), len(f) / 2)
    )
    pf_df["face_landmarks_aspect_ratio"] = pf_df["face_landmarks_array"].apply(
        lambda f: 0
        if (np.max(np.array(f)[:, 1]) - np.min(np.array(f)[:, 1])) == 0
        else (np.max(np.array(f)[:, 0]) - np.min(np.array(f)[:, 0]))
        / (np.max(np.array(f)[:, 1] - np.min(np.array(f)[:, 1])))
    )

    face_aspect_ratio_mean = pf_df["face_landmarks_aspect_ratio"].mean()
    # face_aspect_ratio_std = pf_df["face_landmarks_aspect_ratio"].std()

    pf_df["aspect_ratio_dev"] = pf_df["face_landmarks_aspect_ratio"].apply(
        lambda f: abs(f - face_aspect_ratio_mean)
    )

    # pf_df["face_embedding"] = pf_df["face_embedding"].apply(lambda p: p[:FACE_FEATURES])

    # This selects a single face to represent each track and uses it for clustering
    rep_pf_df = pf_df.iloc[
        (
            # This is always pretty close to 1...
            # pf_df.groupby(["track_id"])["face_confidence"].idxmax()
            pf_df.groupby(["track_id"])["aspect_ratio_dev"].idxmin()
        )
    ]

    logging.info(f"Faces representing a track:  {len(rep_pf_df)}")

    X = rep_pf_df["face_embedding"].to_list()

    clusterable_embedding = pacmap.PaCMAP(
        n_components=2, n_neighbors=None, MN_ratio=0.5, FP_ratio=2.0
    ).fit_transform(X, init="pca")

    logging.info("fitting clustered model")

    # clst = HDBSCAN(min_cluster_size=3, min_samples=4)  # , max_cluster_size=15
    clst = KMeans(int(args.n_clusters))
    clst.fit(clusterable_embedding)
    labels = clst.labels_.tolist()

    assigned_faces = 0

    logging.info(f"{max(labels)} clusters found")

    face_clusters = []
    for i, cluster_id in enumerate(labels):
        if cluster_id == -1:
            continue

        face_clusters.append([video_id, cluster_id, int(rep_pf_df.iloc[i]["track_id"])])

    logging.info(
        f"Assigning {len(face_clusters)} total face clusters by track in the DB"
    )

    await db.assign_face_clusters_by_track(face_clusters)

    for cluster_id in range(-1, max(labels) + 1):
        if cluster_id != -1:
            assigned_faces += labels.count(cluster_id)

    logging.info(
        f"assigned {assigned_faces} track faces out of {len(labels)}, {round(assigned_faces/len(labels),4)}"
    )

    logging.info("Generating representative face averages for timeline")

    clustered_faces = await db.get_clustered_face_data_from_video(video_id)

    cluster_images = {}

    i = -1
    # Draw representative faces for each cluster
    for cluster_face in clustered_faces:
        i += 1

        if i != 0 and i % FACE_SAMPLE_RATE != 0:
            continue

        logging.info(
            f"Sampling face {i} out of {len(clustered_faces)} for cluster average"
        )

        # try:
        #     cluster_face = rep_pf_df.iloc[i]
        # except Exception as e:
        #     logging.error(f"Error referencing face {i}")
        #     continue

        cluster_id = cluster_face["cluster_id"]

        if cluster_id not in cluster_images:
            cluster_images[cluster_id] = []

        x, y, w, h = [round(coord) for coord in cluster_face["bbox"]]
        video_handle = f"/videos/{video_name}"
        img = iio.imread(video_handle, index=cluster_face["frame"] - 1, plugin="pyav")
        img_region = img[y : y + h, x : x + w]

        # Resize/normalize the cutout background dimensions, just as is done
        # for the pose itself
        resized_image = cv2.resize(
            img_region,
            dsize=(WIDTH_THRESHOLD * UPSCALE, WIDTH_THRESHOLD * UPSCALE),
            interpolation=cv2.INTER_LANCZOS4,
        )
        cluster_images[cluster_id].append(resized_image)

    for cluster_id in cluster_images:
        images_array = np.array(cluster_images[cluster_id], dtype=float)

        # Average the RGB values of all of the face excerpts
        avg_background_img = np.mean(images_array, axis=0).astype(np.uint8)
        avg_pil_img = Image.fromarray(avg_background_img)

        if not os.path.isdir(f"face_images/{video_name}"):
            os.makedirs(f"face_images/{video_name}")

        avg_pil_img.save(f"face_images/{video_name}/{cluster_id}.png")


if __name__ == "__main__":
    asyncio.run(main())
