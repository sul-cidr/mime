#!/usr/bin/env python3

"""CLI to find non-moving poses and extract their images and pose features for use by PosePlot (nee PixPlot)"""

import argparse
import asyncio
import json
import logging
import math
import os
from collections import OrderedDict, defaultdict
from pathlib import Path

import imageio.v3 as iio
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# import rasterfairy
from PIL import Image, ImageDraw
from pointgrid import align_points_to_grid
from rich.logging import RichHandler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from umap import UMAP

from lib.pose_drawing import (
    UPSCALE,
    draw_armatures,
    draw_normalized_and_unflattened_pose,
    get_armature_prevalences,
    pad_and_excerpt_image,
)
from mime_db import MimeDb

# import sys

DEFAULT_CLUSTERS = 15  # Expected number of pose clusters
OUTPUT_VOL = "../extras"

# PixPlot variables
ATLAS_SIZE = 2048
CELL_SIZE = 32
LOD_CELL_HEIGHT = 128


# PixPlot utility function(s)
def save_atlas(atlas, out_dir, n):
    """Save an atlas image to disk"""
    out_path = os.path.join(out_dir, f"atlas-{n}.jpg")
    atlas = atlas.astype(np.uint8)
    im = Image.fromarray(atlas, "RGB")
    im.save(out_path)


def resize_to_max(im, n):
    """
    Resize PIL image so its longest side has n pixels (maintain proportion)
    and return a NumPy array
    """
    w, h = im.size
    size = (n, int(n * h / w)) if w > h else (int(n * w / h), n)
    return np.asarray(im.resize(size))


def resize_to_height(im, height):
    """
    Resize PIL image to height h and proportional width
    """
    w, h = im.size
    if (w / h * height) < 1:
        resizedwidth = 1
    else:
        resizedwidth = int(w / h * height)
    size = (resizedwidth, height)
    return np.asarray(im.resize(size))


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
        "--video-path",
        action="store",
        required=True,
        help="The path to the video file (with extension)",
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

    video_path = Path(args.video_path)
    video_name = video_path.name

    # This is where PixPlot expects to find the layout data
    data_path = Path(OUTPUT_VOL, "poseplot", video_name, "data")
    os.makedirs(data_path, exist_ok=True)

    # This is the base path to use when referring to local assets in manifest.json
    output_path = Path("data")

    # Connect to the database
    db = await MimeDb.create()

    # Get video metadata
    video_id = await db.get_video_id(video_name)

    video_data = await db.get_video_by_id(video_id)
    video_fps = video_data["fps"]

    video_movelets = await db.get_movelet_data_from_video(video_id)
    movelets_df = pd.DataFrame.from_records(
        video_movelets, columns=video_movelets[0].keys()
    )

    # The poses are needed in addition to movelets to get individual pose excerpts
    video_poses = await db.get_pose_data_from_video(video_id)
    # video_poses = await db.get_poses_with_faces(video_id)
    poses_df = pd.DataFrame.from_records(video_poses, columns=video_poses[0].keys())

    # Some stats about the amount of motion in the movelets
    logging.info("TOTAL MOVELETS: %d", len(movelets_df))
    logging.info("NULL MOVELETS: %d", len(movelets_df[movelets_df["movement"].isna()]))
    logging.info(
        "MOVELETS WITH 0 MOVEMENT: %d", len(movelets_df[movelets_df["movement"] == 0])
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
    nonnull_movelets_df.fillna({"movement": -1}, inplace=True)

    # Any movelet with motion less than the mode of the motion histogram is "static"
    # and thus can be used to extract a represenative pose
    n, bins, _ = plt.hist(
        nonnull_movelets_df[nonnull_movelets_df["movement"] <= 500]["movement"],
        bins=300,
    )
    # plt.xlabel("Movement (normalized pixels/sec)")
    # plt.ylabel("# Movelets")
    top_bin = n[1:].argmax()
    # logging.info('most frequent bin: (' + str(bins[top_bin]) + ',' + str(bins[top_bin+1]) + ')')
    # logging.info('mode: '+ str((bins[top_bin] + bins[top_bin+1])/2))
    movement_mode = (bins[top_bin] + bins[top_bin + 1]) / 2

    static_movelets = movelets_df[
        (movelets_df["movement"] >= 0) & (movelets_df["movement"] < movement_mode)
    ].reset_index()
    # XXX Use POEM viewpoint-invariant embedding features for clustering and embedding
    static_poses = static_movelets["poem_embedding"].tolist()
    static_norms = static_movelets["norm"].tolist()

    logging.info(f"TOTAL LOW-MOTION POSES: {len(static_poses)}")

    # Extract representative pose images and keep track of their metadata
    images_dir = Path(data_path, "originals")
    os.makedirs(images_dir, exist_ok=True)
    img_metadata = []

    # PixPlot metadata elements:
    # year is an integer but doesn't need to be a year
    # label can be the cluster the pose is in
    # description is plain text
    # can also supply any number of "tags", but it's not clear how these would be useful

    # Won't need to save image (pose) features with a fully lobotomized PixPlot viewer
    # features_dir = f"{OUTPUT_PATH}/input/{video_name}/pose_features"
    # if not os.path.isdir(features_dir):
    #     os.makedirs(features_dir, exist_ok=True)

    all_image_paths = []

    match_failures = 0

    # Grab a pose from (ideally) somewhere in the middle of the movelet to use
    # as the representative excerpt of the pose
    for movelet in static_movelets.to_dict("records"):
        # Prefer a target frame in the middle of the movelet, but if the actual pose
        # index is missing from this frame (which can happen sometimes), just use the
        # first frame of the movelet
        try:
            target_frame = round((movelet["end_frame"] + movelet["start_frame"]) / 2)
            target_movelet = poses_df[
                (poses_df["frame"] == target_frame)
                & (poses_df["track_id"] == movelet["track_id"])
            ]
            if len(target_movelet) == 0:
                target_frame = movelet["start_frame"]
                target_movelet = poses_df[
                    (poses_df["frame"] == target_frame)
                    & (poses_df["track_id"] == movelet["track_id"])
                ]
            target_pose = poses_df[
                (poses_df["frame"] == target_frame)
                & (poses_df["track_id"] == movelet["track_id"])
            ].iloc[0]
        except Exception:
            logging.info(
                "Couldn't find representative pose from movelet middle or beginning, skipping"
            )
            match_failures += 1
            continue

        save_name = f"{images_dir}/{target_frame}_{target_pose['pose_idx']}.jpg"

        # Cut the pose out of the video frame and draw the armature on top of it
        if not os.path.isfile(save_name):
            logging.info(f"Extracting pose from frame {save_name}")

            # This is always truncated at the edges of the image, which we don't want
            # pose_bbox = [round(v) for v in target_pose["bbox"]]

            keypoints_triples = [
                (
                    target_pose["keypointsopp"][i],
                    target_pose["keypointsopp"][i + 1],
                    target_pose["keypointsopp"][i + 2],
                )
                for i in range(0, len(target_pose["keypointsopp"]), 3)
            ]

            keypoints_array = np.array(keypoints_triples)

            pose_min_x = round(np.min(keypoints_array[:, 0]))
            pose_max_x = round(np.max(keypoints_array[:, 0]))
            pose_min_y = round(np.min(keypoints_array[:, 1]))
            pose_max_y = round(np.max(keypoints_array[:, 1]))

            pose_width = pose_max_x - pose_min_x
            pose_height = pose_max_y - pose_min_y

            bbox = [pose_min_x, pose_min_y, pose_width, pose_height]

            # Add the face to the pose extent if present
            frame_faces = await db.get_frame_faces(video_id, target_frame)

            if len(frame_faces):
                faces_df = pd.DataFrame.from_records(
                    frame_faces, columns=frame_faces[0].keys()
                )

                target_face = faces_df[faces_df["pose_idx"] == target_pose["pose_idx"]]
                if len(target_face):
                    target_face_df = target_face.iloc[0]
                    face_bbox = [round(v) for v in target_face_df["bbox"]]

                    min_x = min(pose_min_x, face_bbox[0])
                    min_y = min(pose_min_y, face_bbox[1])
                    max_x = max(pose_max_x, face_bbox[0] + face_bbox[2])
                    max_y = max(pose_max_y, face_bbox[1] + face_bbox[3])
                    b_w = max_x - min_x
                    b_h = max_y - min_y

                    # A bbox that includes the body and the face (if detected)
                    bbox = [min_x, min_y, b_w, b_h]

            frame_image = Path(
                "/static", str(video_id), "frames", f"{target_frame}.jpeg"
            )
            if frame_image.exists():
                pose_frame_image = iio.imread(frame_image)
            else:
                pose_frame_image = iio.imread(
                    f"/videos/{video_name}", index=target_frame - 1, plugin="pyav"
                )

            pose_img_region = pad_and_excerpt_image(
                pose_frame_image, bbox[0], bbox[1], bbox[2], bbox[3]
            )

            pose_img = Image.fromarray(pose_img_region)

            img_size = pose_img.size

            pose_img = pose_img.resize((img_size[0] * UPSCALE, img_size[1] * UPSCALE))
            drawing = ImageDraw.Draw(pose_img)

            # Shift the armature coordinates to match the cropped image
            shifted_triples = [
                [triple[0] - bbox[0], triple[1] - bbox[1], triple[2]]
                for triple in keypoints_triples
            ]

            drawing = draw_armatures(shifted_triples, drawing, coco_coords=17)

            pose_img = pose_img.resize(
                (img_size[0], img_size[1]), resample=Image.Resampling.LANCZOS
            )

            pose_img.save(save_name)

            pose_img.close()

        frame_minute = round(target_frame / video_fps / 60)

        img_metadata.append(
            {
                "filename": f"{target_frame}_{target_pose['pose_idx']}.jpg",
                "description": f"Frame {target_frame} | pose {target_pose['pose_idx']} | track {target_pose['track_id']}",
                "year": str(frame_minute),
            }
        )

        all_image_paths.append(save_name)

    # Write metadata in desired format for PixPlot
    out_dir = Path(data_path, "metadata")
    for i in ["filters", "options", "file"]:
        out_path = Path(out_dir, i)
        os.makedirs(out_path, exist_ok=True)
    # create the lists of images with each tag
    d = defaultdict(list)
    for i in img_metadata:
        filename = i["filename"]
        i["tags"] = [j.strip() for j in i.get("tags", "").split("|")]
        for j in i["tags"]:
            d["__".join(j.split())].append(filename)
        with open(
            Path(out_dir, "file", filename + ".json"), "w", encoding="utf-8"
        ) as outfile:
            json.dump(i, outfile, indent=4)
    # This is the master list of filters (often there are none)
    with open(
        Path(out_dir, "filters", "filters.json"), "w", encoding="utf-8"
    ) as outfile:
        json.dump(
            [
                {
                    "filter_name": "select",
                    "filter_values": list(d.keys()),
                }
            ],
            outfile,
            indent=4,
        )

    # create the options for the category dropdown
    for i in d:
        with open(
            Path(out_dir, "options", i + ".jon"), "w", encoding="utf-8"
        ) as outfile:
            json.dump(d[i], outfile, indent=4)
    # create the map from sequence number to images with that seqno (if present)
    date_d = defaultdict(list)
    all_dates = []
    for i in img_metadata:
        date = i.get("year", "")
        if date:
            date_d[date].append(i["filename"])
            all_dates.append(date)
    # find the min and max dates to show on the date slider
    # dates = np.array([int(i.strip()) for i in date_d if isinstance(i, int)])
    dates = np.array([int(key) for key in date_d.keys()])
    domain = {"min": int(min(dates)), "max": int(max(dates))}
    # mean = np.mean(dates)
    # std = np.std(dates)
    # for i in dates:
    #     # update the date domain with all non-outlier dates
    #     if abs(mean - i) < (std * 4):
    #         domain["min"] = int(min(i, domain["min"]))
    #         domain["max"] = int(max(i, domain["max"]))
    # write the dates json
    if len(date_d) > 1:
        with open(Path(out_dir, "dates.json"), "w", encoding="utf-8") as outfile:
            json.dump(
                {
                    "domain": domain,
                    "dates": date_d,
                },
                outfile,
                indent=4,
            )

    # Get the main embedding
    logging.info("Computing PCA decomposition")
    # n_components = 16 = the length of a POEM embedding
    pca_decomposition = PCA(n_components=16).fit_transform(static_poses)

    logging.info("Computing UMAP embedding")
    umap_embedding = UMAP(
        n_components=2, n_neighbors=100, min_dist=0.5, metric="euclidean"
    ).fit_transform(
        # static_poses
        pca_decomposition
    )

    umap_embedding = umap_embedding / 4

    # main embedding (UMAP) layout
    out_path = Path(data_path, "layouts")
    os.makedirs(out_path, exist_ok=True)
    if isinstance(umap_embedding, np.ndarray):
        main_embedding = umap_embedding.tolist()
    with open(Path(out_path, "umap.json"), "w", encoding="utf-8") as outfile:
        json.dump(main_embedding, outfile, indent=4)

    # jittered embedding layout
    jittered_embedding = align_points_to_grid(umap_embedding, fill=0.01).tolist()
    with open(Path(out_path, "umap-jittered.json"), "w", encoding="utf-8") as outfile:
        json.dump(jittered_embedding, outfile, indent=4)

    umap_desc = {
        "variants": [
            {
                "n_neighbors": 15,
                "min_dist": 0.01,
                "jittered": str(Path(output_path, "layouts", "umap-jittered.json")),
                "layout": str(Path(output_path, "layouts", "umap.json")),
            }
        ]
    }

    # layout alphabetical by filename
    n = math.ceil(len(all_image_paths) ** (1 / 2))
    alphabetic_layout = []  # positions
    for i, _ in enumerate(all_image_paths):
        x = i % n
        y = math.floor(i / n)
        alphabetic_layout.append([x, y])
    with open(Path(data_path, "layouts", "grid.json"), "w", encoding="utf-8") as outfile:
        json.dump(alphabetic_layout, outfile, indent=4)

    # embedding layout, but squashed into a grid
    # XXX rasterfairy (whether the Yale DH version or upstream) is out of date
    # grid_path = Path(data_path, "layouts", "rasterfairy.json")
    # grid_umap = (umap_embedding + 1) / 2  # scale 0:1
    # try:
    #     grid_umap = rasterfairy.coonswarp.rectifyCloud(
    #         grid_umap,  # stretch the distribution
    #         perimeterSubdivisionSteps=4,
    #         autoPerimeterOffset=False,
    #         paddingScale=1.05,
    #     )
    # except Exception as exc:
    #     logging.error(f"Coonswarp rectification could not be performed: {exc}")
    # pos = rasterfairy.transformPointCloud2D(grid_umap)[0]
    # with open(grid_path, "w", encoding="utf-8") as outfile:
    #     json.dump(pos, outfile, indent=4)

    # "Date" layout (actually just frame numbers converted to minutes)

    d = defaultdict(list)
    for idx, i in enumerate(all_dates):
        d[i].append(idx)

    n_coords_y = 0
    n_coords_x = -1

    cols = 2
    while n_coords_y > n_coords_x:
        cols = cols * 2
        n_coords_x = (cols + 1) * len(d)
        n_coords_y = 1 + max([len(d[i]) for i in d]) // cols

    logging.info(f"Creating date layout with {cols} columns")

    # create a mesh of grid positions in clip space -1:1 given the time distribution
    grid_x = (np.arange(0, n_coords_x) / (n_coords_x - 1)) * 2
    grid_y = (np.arange(0, n_coords_y) / (n_coords_x - 1)) * 2
    # divide each grid axis by half its max length to center at the origin 0,0
    grid_x = grid_x - np.max(grid_x) / 2.0
    grid_y = grid_y - np.max(grid_y) / 2.0
    # make dates increase from left to right by sorting keys of d
    d_keys = np.array(list(d.keys()))
    # seconds = np.array([date_to_seconds(dates[ d[i][0] ]) for i in d_keys])
    seconds = np.array([all_dates[d[i][0]] for i in d_keys])
    d_keys = d_keys[np.argsort(np.array(seconds).astype(int))]
    # determine which images will fill which units of the grid established above
    coords = np.zeros(
        (len(all_dates), 2)
    )  # 2D array with x, y clip-space coords of each date
    for jdx, j in enumerate(d_keys):
        for kdx, k in enumerate(d[j]):
            x = jdx * (cols + 1) + (kdx % cols)
            y = kdx // cols
            coords[k] = [grid_x[x], grid_y[y]]
    # find the positions of labels
    label_positions = np.array(
        [[grid_x[i * (cols + 1)], grid_y[0]] for i in range(len(d))]
    )
    # move the labels down in the y dimension by a grid unit
    dx = grid_x[1] - grid_x[0]  # size of a single cell
    label_positions[:, 1] = label_positions[:, 1] - dx
    # quantize the label positions and label positions
    image_positions = [[round(float(j), 5) for j in i] for i in coords]
    label_positions = [[round(float(j), 5) for j in i] for i in label_positions.tolist()]

    positions_out_path = Path(data_path, "layouts", "timeline.json")
    with open(positions_out_path, "w", encoding="utf-8") as outfile:
        json.dump(image_positions, outfile)
    labels_out_path = Path(data_path, "layouts", "timeline-labels.json")
    date_layout = {"positions": label_positions, "labels": d_keys.tolist(), "cols": cols}
    with open(labels_out_path, "w", encoding="utf-8") as outfile:
        json.dump(date_layout, outfile)

    # write and return the paths to the date based layout
    date_layout_info = {
        "layout": str(Path("data", "layouts", "timeline.json")),
        "labels": str(Path("data", "layouts", "timeline-labels.json")),
    }

    layouts = {
        "umap": umap_desc,
        "alphabetic": {
            "layout": str(Path(output_path, "layouts", "grid.json")),
        },
        "grid": {
            "layout": None,  # grid_path,
        },
        "categorical": None,  # get_categorical_layout(**kwargs),
        "date": date_layout_info,
        "geographic": None,  # get_geographic_layout(**kwargs),
        "custom": None,  # get_custom_layout(**kwargs),
    }

    # Clustering will be used later
    clst = KMeans(int(args.n_clusters))
    est = clst.fit(umap_embedding)
    # labels = clst.labels_.tolist()

    # Assign the explorer clusters to the DB so that the poses timeline tab
    # shows the same clusters as the explorer
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

    # Also assign the movelet cluster IDs in the DB

    filtered_movelet_indices = []

    movelet_clusters = []
    for cluster_id in range(max(labels) + 1):
        logging.info(f"Poses in cluster {cluster_id}: {labels.count(cluster_id)}")

        cluster_track_poses = {}
        for movelet_id in cluster_to_poses[cluster_id]:
            this_movelet = static_movelets.iloc[movelet_id]
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

    filtered_movelet_counts = {}
    for i in filtered_movelet_indices:
        filtered_movelet_counts[i] = filtered_movelet_counts.get(i, 0) + 1

    logging.info("Filtered movelets: %d", len(set(filtered_movelet_indices)))
    filtered_movelets = static_movelets.iloc[list(set(filtered_movelet_indices))]
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
            cl_pose = static_norms[pose_index]
            cl_pose[cl_pose == -1] = np.nan
            cluster_poses.append(cl_pose)
        cluster_average = np.nanmean(np.array(cluster_poses), axis=0).tolist()
        armature_prevalences = get_armature_prevalences(cluster_poses)
        cluster_average = np.array_split(cluster_average, len(cluster_average) / 2)
        cluster_average_img = draw_normalized_and_unflattened_pose(
            cluster_average, armature_prevalences=armature_prevalences
        )
        cluster_average_img.save(f"pose_cluster_images/{video_name}/{cluster_id}.png")
        os.makedirs(Path(data_path, "pose_cluster_images"), exist_ok=True)
        cluster_average_img.save(
            Path(data_path, "pose_cluster_images", f"{cluster_id}.png")
        )

    # create a map from cluster label to image indices in cluster
    d = defaultdict(lambda: defaultdict(list))
    for idx, i in enumerate(est.labels_):
        if i != -1:
            d[i]["images"].append(idx)
            d[i]["img"] = os.path.basename(all_image_paths[idx])
            d[i]["avg_img"] = f"{i}.png"
            d[i]["layout"] = "vectors"
    # remove massive clusters
    # deletable = []
    # for i in d:
    #     # find percent of images in cluster
    #     image_percent = len(d[i]["images"]) / len(all_image_paths)
    #     # determine if image or area percent is too large
    #     if image_percent > 0.5:
    #         deletable.append(i)
    # for i in deletable:
    #     del d[i]
    # sort the clusers by size and then label the clusters
    clusters = d.values()
    clusters = sorted(clusters, key=lambda i: len(i["images"]), reverse=True)
    for idx, i in enumerate(clusters):
        i["label"] = f"Cluster {idx + 1}"
    # slice off the first `max_clusters`
    clusters = clusters[: int(args.n_clusters)]
    # save the hotspots to disk and return the path to the saved json
    logging.info(f"Found {len(clusters)} hotspots")
    clusters_path = Path(data_path, "hotspots")
    os.makedirs(clusters_path, exist_ok=True)
    with open(Path(clusters_path, "hotspot.json"), "w", encoding="utf-8") as outfile:
        json.dump(clusters, outfile, indent=4)

    # Generate and save to disk all atlases to be used for this visualization
    # If square, center each cell in an nxn square, else use uniform height
    out_dir = Path(data_path, "atlases")
    os.makedirs(out_dir, exist_ok=True)
    # create the atlas images and store the positions of cells in atlases
    logging.info("Creating atlas files")
    n = 0  # number of atlases
    x = 0  # x pos in atlas
    y = 0  # y pos in atlas
    atlas_data = []  # l[cell_idx] = atlas data
    atlas = np.zeros((ATLAS_SIZE, ATLAS_SIZE, 3))
    for i in all_image_paths:
        im = Image.open(i)
        cell_data = resize_to_height(im, CELL_SIZE)
        _, v, _ = cell_data.shape
        appendable = False
        if (x + v) <= ATLAS_SIZE:
            appendable = True
        elif (y + (2 * CELL_SIZE)) <= ATLAS_SIZE:
            y += CELL_SIZE
            x = 0
            appendable = True
        if not appendable:
            save_atlas(atlas, out_dir, n)
            n += 1
            atlas = np.zeros((ATLAS_SIZE, ATLAS_SIZE, 3))
            x = 0
            y = 0
        atlas[y : y + CELL_SIZE, x : x + v] = cell_data
        # find the size of the cell in the lod canvas
        lod_data = resize_to_max(im, LOD_CELL_HEIGHT)
        h, w, _ = lod_data.shape  # h,w,colors in lod-cell sized image `i`
        atlas_data.append(
            {
                "idx": n,  # atlas idx
                "x": x,  # x offset of cell in atlas
                "y": y,  # y offset of cell in atlas
                "w": w,  # w of cell at lod size
                "h": h,  # h of cell at lod size
            }
        )
        x += v
    save_atlas(atlas, out_dir, n)
    out_path = os.path.join(out_dir, "atlas_positions.json")
    with open(out_path, "w", encoding="utf-8") as out:
        json.dump(atlas_data, out, indent=4)

    # Create the base object for the manifest output file
    atlas_ids = {i["idx"] for i in atlas_data}
    sizes = [[] for _ in atlas_ids]
    pos = [[] for _ in atlas_ids]
    for i in atlas_data:
        sizes[i["idx"]].append([i["w"], i["h"]])
        pos[i["idx"]].append([i["x"], i["y"]])

    # XXX Not clear (yet) why this would be needed
    # create a heightmap for the umap layout
    # if "umap" in layouts and layouts["umap"]:
    #    get_heightmap(layouts["umap"]["variants"][0]["layout"], "umap", **kwargs)

    # specify point size scalars
    point_sizes = {}
    point_sizes["min"] = 0
    point_sizes["grid"] = 1 / math.ceil(len(all_image_paths) ** (1 / 2))
    point_sizes["max"] = point_sizes["grid"] * 1.5
    point_sizes["scatter"] = point_sizes["grid"] * 1
    point_sizes["initial"] = point_sizes["scatter"]
    point_sizes["categorical"] = point_sizes["grid"] * 1
    point_sizes["geographic"] = point_sizes["grid"] * 0.025
    # fetch the date distribution data for point sizing
    point_sizes["date"] = 2 / ((date_layout["cols"] + 1) * len(date_layout["labels"]))
    # create manifest json
    manifest = {
        "version": "Pose_Plot_0.0.1",
        # "plot_id": UUID,
        "output_directory": "data",
        "layouts": layouts,
        "initial_layout": "umap",
        "point_sizes": point_sizes,
        "imagelist": str(Path(output_path, "imagelists", "imagelist.json")),
        "atlas_dir": str(Path(output_path, "atlases")),
        "metadata": True,
        "default_hotspots": str(Path(output_path, "hotspots", "hotspot.json")),
        "custom_hotspots": False,  # PATH TO USER HOTSPOTS, APPARENTLY
        # "gzipped": kwargs["gzip"],
        "config": {
            "sizes": {
                "atlas": ATLAS_SIZE,
                "cell": CELL_SIZE,
                "lod": LOD_CELL_HEIGHT,
            },
        },
        # "creation_date": datetime.datetime.today().strftime("%d-%B-%Y-%H:%M:%S"),
    }
    # write the manifest without gzipping
    # no_gzip_kwargs = {
    #     "out_dir": kwargs["out_dir"],
    #     "gzip": False,
    #     "plot_id": kwargs["plot_id"],
    # }
    # manifest_path = Path("output", "manifests", "manifest")
    # json.dump(manifest, open(manifest_path, "w", encoding="utf-8")
    manifest_path = Path(data_path, "manifest.json")
    json.dump(manifest, open(manifest_path, "w", encoding="utf-8"), indent=4)
    # create images json
    imagelist = {
        "cell_sizes": sizes,
        "images": [os.path.basename(i) for i in all_image_paths],
        "atlas": {
            "count": len(atlas_ids),
            "positions": pos,
        },
    }
    os.makedirs(Path(data_path, "imagelists"), exist_ok=True)
    with open(
        Path(data_path, "imagelists", "imagelist.json"), "w", encoding="utf-8"
    ) as outfile:
        json.dump(imagelist, outfile, indent=4)

    # Write all original images and thumbs to the output dir
    for im_path in all_image_paths:
        im = Image.open(im_path)
        filename = os.path.basename(im_path)
        # copy original for lightbox
        out_dir = Path(data_path, "originals")
        os.makedirs(out_dir, exist_ok=True)
        out_path = Path(out_dir, filename)
        if not os.path.exists(out_path):
            resized = resize_to_height(im, 600)
            resized = Image.fromarray(resized)
            resized.save(out_path)
        # copy thumb for lod texture
        out_dir = Path(data_path, "thumbs")
        os.makedirs(out_dir, exist_ok=True)
        out_path = Path(out_dir, filename)
        img = Image.fromarray(resize_to_max(im, LOD_CELL_HEIGHT))
        img.save(out_path)

    # Use the below if the number of images, features and metadata entries are
    # not equal
    """
    imgs_to_keep = set()

    with open(f"{video_name}/{video_name}.csv", "r", newline="", encoding="utf-8") as img_metadata_fp:
        img_metadata_file = csv.reader(img_metadata_fp)
        for la in img_metadata_file:
            img_fn = la[0]
            if img_fn == "filename":
                continue
            imgs_to_keep.add(img_fn)

    print(len(imgs_to_keep),"unique images in metadata file")

    for fn in os.listdir(images_dir):
        if os.path.isfile(f"{images_dir}/{fn}"):
            if fn not in imgs_to_keep:
                print("Deleting image", fn)
                os.unlink(f"{images_dir}/{fn}")
                os.unlink(f"{features_dir}/{fn.replace('jpg', 'npy')}")
    """


if __name__ == "__main__":
    asyncio.run(main())
