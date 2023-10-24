#!/usr/bin/env python3

"""CLI to cluster detected faces for a video in the db."""

import argparse
import asyncio
import logging
from pathlib import Path

# import imageio.v3 as iio
import numpy as np
import pandas as pd
import umap
from mime_db import MimeDb
from rich.logging import RichHandler
from sklearn.cluster import KMeans

# from PIL import Image

# DeepFace and ArcFace resize/crop face images to 152x152 and 112x112 pixels,
# respectively, so an image upsized from smaller than 100xH px is not useful.
WIDTH_THRESHOLD = 100  # pixels of width
DEFAULT_CLUSTERS = 15  # Expected number of face clusters
FACE_FEATURES = 512  # 4096 for DeepFace, 512 for ArcFace


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

    pf_df["face_width"] = pf_df.apply(
        lambda p: 0 if p["face_bbox"] is None else p["face_bbox"][2], axis=1
    )

    logging.info(f"Total poses with faces: {len(pf_df)}")

    pf_df = pf_df[
        (
            (~np.isnan(pf_df["face_confidence"]))
            & (pf_df["face_confidence"] > 0)
            # & (pf_df["face_width"] > WIDTH_THRESHOLD)
        )
    ].reset_index()

    logging.info(f"Poses with usable faces: {len(pf_df)}")

    # We can use the largest face image as a thumbnail/rep (if desired)
    pf_df["face_area"] = pf_df.apply(
        lambda p: 0
        if p["face_bbox"] is None
        else p["face_bbox"][2] * p["face_bbox"][3],
        axis=1,
    )

    pf_df["face_avg"] = pf_df.groupby(["track_id"])["face_embedding"].transform(
        average_face_embeddings
    )

    pf_df["face_embedding"] = pf_df["face_embedding"].apply(lambda p: p[:FACE_FEATURES])

    # This selects a single face to represent each track and uses it for clustering
    rep_pf_df = pf_df.iloc[
        (
            # poses_df.groupby(["track_id"])["face_area"].idxmax()
            # This is always pretty close to 1...
            pf_df.groupby(["track_id"])["face_confidence"].idxmax()
        )
    ]

    logging.info(f"Faces representing a track:  {len(rep_pf_df)}")

    X = rep_pf_df["face_embedding"].to_list()

    # im_labels = (
    #     rep_pf_df[["track_id", "frame"]].map(str).agg("_".join, axis=1).to_list()
    # )
    # standard_embedding = umap.UMAP(
    #     random_state=42,
    # ).fit_transform(X)

    clusterable_embedding = umap.UMAP(
        n_neighbors=10,
        min_dist=0.0,
        n_components=2,
        random_state=42,
    ).fit_transform(X)

    logging.info("fitting clustered model")

    # clst = HDBSCAN(min_cluster_size=3, min_samples=4)  # , max_cluster_size=15
    clst = KMeans(int(args.n_clusters))
    # embedding = standard_embedding
    embedding = clusterable_embedding
    clst.fit(embedding)
    # clst.fit(X) # Won't be plottable
    labels = clst.labels_.tolist()

    assigned_faces = 0

    logging.info(f"{max(labels)} clusters found")

    for i, cluster_id in enumerate(labels):
        if cluster_id == -1:
            continue

        logging.info(
            f"assigning cluster {cluster_id} to track {int(rep_pf_df.iloc[i]['track_id'])}"
        )
        await db.assign_face_clusters_by_track(
            video_id, cluster_id, int(rep_pf_df.iloc[i]["track_id"])
        )

    for cluster_id in range(-1, max(labels) + 1):
        if cluster_id != -1:
            assigned_faces += labels.count(cluster_id)

    logging.info(
        f"assigned {assigned_faces} track faces out of {len(labels)}, {round(assigned_faces/len(labels),4)}"
    )

    # Draw representative faces for each cluster
    # Commented out here for now, but may be useful in the future
    # for i, cluster_id in enumerate(labels):
    #     try:
    #         cluster_pose = rep_pf_df.iloc[i]
    #     except Exception as e:
    #         print("Error referencing face", i)
    #         print(e)
    #         continue
    #     x, y, w, h = [round(coord) for coord in cluster_pose["face_bbox"]]
    #     video_handle = f"/videos/{video_name}"
    #     img = iio.imread(video_handle, index=cluster_pose["frame"] - 1, plugin="pyav")
    #     img_region = img[y : y + h, x : x + w]
    #     iio.imwrite(f"{cluster_id}/{i}.jpg", img_region, extension=".jpeg")


if __name__ == "__main__":
    asyncio.run(main())
