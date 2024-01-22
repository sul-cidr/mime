#!/usr/bin/env python3

"""CLI to cluster detected poses for a video in the db."""

import argparse
import asyncio
import logging
import os
from collections import OrderedDict
from pathlib import Path

# import imageio.v3 as iio
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import umap
from rich.logging import RichHandler
from sklearn.cluster import KMeans

from lib.pose_drawing import *
from mime_db import MimeDb

# from PIL import Image

DEFAULT_CLUSTERS = 15  # Expected number of pose clusters


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
        help="The desired number of pose clusters to find",
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

    video_movelets = await db.get_movelet_data_from_video(video_id)
    movelets_df = pd.DataFrame.from_records(
        video_movelets, columns=video_movelets[0].keys()
    )

    # video_poses = await db.get_pose_data_from_video(video_id)
    # poses_df = pd.DataFrame.from_records(video_poses, columns=video_poses[0].keys())

    logging.info("TOTAL MOVELETS: %d", len(movelets_df))
    logging.info(
        "NULL MOTION MOVELETS: %d", len(movelets_df[movelets_df["movement"].isna()])
    )
    logging.info(
        "MOVELETS WITH STILL MOTION: %d", len(movelets_df[movelets_df["movement"] == 0])
    )
    logging.info(
        "MOVELETS WITH MOVEMENT < 10px/sec: %d",
        len(
            movelets_df[(movelets_df["movement"] >= 0) & (movelets_df["movement"] < 10)]
        ),
    )

    logging.info(
        "MEAN MOVEMENT PER MOVELET (norm px/sec): %d",
        np.nanmean(movelets_df["movement"]),
    )
    logging.info(
        "MEDIAN MOVEMENT PER MOVELET (norm px/sec): %d",
        np.nanmedian(movelets_df["movement"]),
    )

    nonnull_movelets_df = movelets_df.copy()
    nonnull_movelets_df["movement"].fillna(-1, inplace=True)

    n, bins, patches = plt.hist(
        nonnull_movelets_df[nonnull_movelets_df["movement"] <= 500]["movement"],
        bins=300,
    )
    # plt.xlabel("Movement (normalized pixels/sec)")
    # plt.ylabel("# Movelets")
    top_bin = n[1:].argmax()
    # logging.info('most frequent bin: (' + str(bins[top_bin]) + ',' + str(bins[top_bin+1]) + ')')
    # logging.info('mode: '+ str((bins[top_bin] + bins[top_bin+1])/2))
    movement_mode = (bins[top_bin] + bins[top_bin + 1]) / 2

    frozen_movelets = movelets_df[
        (movelets_df["movement"] >= 0) & (movelets_df["movement"] < movement_mode)
    ].reset_index()
    frozen_poses = frozen_movelets["norm"].tolist()

    clusterable_embedding = umap.UMAP(
        n_neighbors=10,
        min_dist=1.0,
        n_components=2,
        random_state=42,
    ).fit_transform(frozen_poses)

    logging.info("fitting clustered model")

    # clst = HDBSCAN(min_cluster_size=3, min_samples=4)  # , max_cluster_size=15
    clst = KMeans(int(args.n_clusters))
    # embedding = standard_embedding
    embedding = clusterable_embedding
    clst.fit(embedding)
    # clst.fit(X) # Won't be plottable
    labels = clst.labels_.tolist()

    assigned_poses = 0
    for cluster_id in range(-1, max(labels) + 1):
        if cluster_id != -1:
            assigned_poses += labels.count(cluster_id)

    logging.info(
        f"assigned {assigned_poses} track poses out of {len(labels)}, "
        f"{round(assigned_poses/len(labels),4)}"
    )

    cluster_to_poses = {}
    for i, cluster_id in enumerate(labels):
        if cluster_id not in cluster_to_poses:
            cluster_to_poses[cluster_id] = [i]
        else:
            cluster_to_poses[cluster_id].append(i)

    # Build an alternative, filtered movelet set that is
    # filtered down to just one movelet per track in a cluster
    # i.e., when more than one pose per track is in a given
    # cluster, just keep the first one. This has the effect
    # of stripping out repeated poses that are part of the
    # same low-motion movelet.

    # Also assign the movelet cluster IDs in the DB while doing this

    filtered_movelet_indices = []

    # tracks_per_cluster = []
    # poses_per_track_per_cluster = []

    movelet_clusters = []
    for cluster_id in range(max(labels) + 1):
        logging.info(f"Poses in cluster {cluster_id}: {labels.count(cluster_id)}")

        cluster_track_poses = {}
        for movelet_id in cluster_to_poses[cluster_id]:
            this_movelet = frozen_movelets.iloc[movelet_id]
            logging.debug(
                f"assigning cluster {cluster_id} to movelet in frames {this_movelet['start_frame']} to {this_movelet['end_frame']}, pose {this_movelet['pose_idx']}"
            )
            movelet_clusters.append(
                (
                    video_id,
                    this_movelet["start_frame"],
                    this_movelet["end_frame"],
                    this_movelet["pose_idx"],
                    cluster_id,
                )
            )

            movelet_track = this_movelet["track_id"]
            if movelet_track not in cluster_track_poses:
                filtered_movelet_indices.append(movelet_id)
            #     cluster_track_poses[movelet_track] = 1 # Include non-clustered poses?
            # else:
            #     cluster_track_poses[movelet_track] += 1

    logging.info(f"Assigning {len(movelet_clusters)} total movelet clusters in the DB")

    await db.assign_movelet_clusters(movelet_clusters)

    # Get the full pose data for each representative movelet from a track in a cluster,
    # to be used to display armatures

    filtered_movelet_counts = dict()
    for i in filtered_movelet_indices:
        filtered_movelet_counts[i] = filtered_movelet_counts.get(i, 0) + 1

    logging.info("Filtered movelets: %d", len(set(filtered_movelet_indices)))
    filtered_movelets = frozen_movelets.iloc[list(set(filtered_movelet_indices))]
    filtered_movelets.reset_index(inplace=True)
    filtered_poses = filtered_movelets["norm"].tolist()
    filtered_poses = [np.nan_to_num(pose, nan=-1) for pose in filtered_poses]

    logging.info("Saving representative cluster images")

    if not os.path.isdir(f"pose_cluster_images/{video_name}"):
        os.makedirs(f"pose_cluster_images/{video_name}")

    ord_cluster_to_poses = OrderedDict(
        sorted(cluster_to_poses.items(), key=lambda x: len(x[1]), reverse=True)
    ).keys()
    for cluster_id in ord_cluster_to_poses:
        cluster_poses = []
        # fig, ax = plt.subplots()
        # fig.set_size_inches(UPSCALE * 100 / fig.dpi, UPSCALE * 100 / fig.dpi)
        # fig.canvas.draw()
        logging.info(
            f"CLUSTER: {cluster_id}, POSES: {len(cluster_to_poses[cluster_id])}"
        )
        for pose_index in cluster_to_poses[cluster_id]:
            cl_pose = frozen_poses[pose_index]
            cl_pose[cl_pose == -1] = np.nan
            cluster_poses.append(cl_pose)
        cluster_average = np.nanmean(np.array(cluster_poses), axis=0).tolist()
        armature_prevalences = get_armature_prevalences(cluster_poses)
        cluster_average = np.array_split(cluster_average, len(cluster_average) / 2)
        cluster_average_img = draw_normalized_and_unflattened_pose(
            cluster_average, armature_prevalences=armature_prevalences
        )
        cluster_average_img.save(f"pose_cluster_images/{video_name}/{cluster_id}.png")
        # plt.figure(figsize=(2,2))
        # plt.imshow(cluster_average_img)
        # plt.imsave(f"pose_cluster_images/{cluster_id}.png")
        # plt.show()


if __name__ == "__main__":
    asyncio.run(main())
