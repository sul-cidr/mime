#!/usr/bin/env python3

"""CLI to find non-moving poses and extract their images and pose features for use by PosePlot (nee PixPlot)"""

import argparse
import asyncio
import csv
import logging
import os
from pathlib import Path

import imageio.v3 as iio
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lib.pose_drawing import UPSCALE, draw_armatures
from mime_db import MimeDb
from PIL import Image, ImageDraw
from rich.logging import RichHandler
from sklearn.metrics.pairwise import nan_euclidean_distances

# import sys

OUTPUT_PATH = "../extras"

# Could be learned from motion distribution or provided as a command-line parameter
MOVEMENT_THRESHOLD = 50


# Could be moved to library if used verbatim in more than one action
def compute_movement(timediff, last_norm, norm):
    if (
        np.isnan(timediff)
        or timediff == 0
        or type(last_norm) == float
        or type(norm) == float
    ):
        return 0  # usually this is the first frame in the movelet
    motion = nan_euclidean_distances([last_norm], [norm])[0]
    return motion / timediff


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

    parser.add_argument("--video-path", action="store", required=True)

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    video_path = Path(args.video_path)
    assert video_path.exists(), f"'{video_path}' does not exist"

    # Create database
    db = await MimeDb.create()

    # Get video metadata
    video_name = video_path.name
    video_id = await db.get_video_id(video_name)
    video_id = video_id[0]["id"]

    video_data = await db.get_video_by_id(video_id)
    video_fps = video_data["fps"]

    video_movelets = await db.get_movelet_data_from_video(video_id)
    movelets_df = pd.DataFrame.from_records(
        video_movelets, columns=video_movelets[0].keys()
    )

    video_poses = await db.get_pose_data_from_video(video_id)
    # video_poses = await db.get_poses_with_faces(video_id)

    poses_df = pd.DataFrame.from_records(video_poses, columns=video_poses[0].keys())

    print("TOTAL MOVELETS:", len(movelets_df))
    print("NON-MOTION MOVELETS:", len(movelets_df[movelets_df["movement"].isna()]))
    print("MOVELETS WITH STILL MOTION:", len(movelets_df[movelets_df["movement"] == 0]))
    print(
        "MOVELETS WITH MOVEMENT < 10px/sec:",
        len(
            movelets_df[(movelets_df["movement"] >= 0) & (movelets_df["movement"] < 10)]
        ),
    )

    print(
        "MEAN MOVEMENT PER MOVELET (norm px/sec):", np.nanmean(movelets_df["movement"])
    )
    print(
        "MEDIAN MOVEMENT PER MOVELET (norm px/sec):",
        np.nanmedian(movelets_df["movement"]),
    )

    nonnull_movelets_df = movelets_df.copy()
    nonnull_movelets_df["movement"].fillna(-1, inplace=True)
    n, bins, _ = plt.hist(
        nonnull_movelets_df[nonnull_movelets_df["movement"] <= 500]["movement"],
        bins=300,
    )
    plt.xlabel("Movement (normalized pixels/sec)")
    plt.ylabel("# Movelets")
    top_bin = n[1:].argmax()
    print(
        "most frequent bin: (" + str(bins[top_bin]) + "," + str(bins[top_bin + 1]) + ")"
    )
    print("mode: " + str((bins[top_bin] + bins[top_bin + 1]) / 2))
    # movement_mode = (bins[top_bin] + bins[top_bin + 1]) / 2

    nonnull_movelets_df.sort_values(
        ["track_id", "tick"], inplace=True, ignore_index=True
    )
    nonnull_movelets_df["next_mvt"] = nonnull_movelets_df.shift(-1)["movement"]

    adjacent_static_movelets_df = nonnull_movelets_df[
        (
            (nonnull_movelets_df["movement"] >= 0)
            & (nonnull_movelets_df["movement"] < MOVEMENT_THRESHOLD)
        )
        | (
            (nonnull_movelets_df["next_mvt"] >= 0)
            & (nonnull_movelets_df["next_mvt"] < MOVEMENT_THRESHOLD)
        )
    ][["track_id", "tick", "movement", "next_mvt"]]

    static_pose_id = 0
    static_movelets = []
    # A static pose movelet is defined by a static_pose_id, track_id, start_frame, end_frame, norm (avg of all components), movement

    for track_id in adjacent_static_movelets_df["track_id"].unique():
        print("Track", track_id)
        track_df = adjacent_static_movelets_df[
            adjacent_static_movelets_df["track_id"] == track_id
        ]
        track_ticks = track_df["tick"].unique()
        start_tick = None
        prev_tick = None
        end_tick = None
        segment_norms = []
        for t in range(len(track_ticks) + 1):
            if t < len(track_ticks):
                tick = track_ticks[t]

            if t == 0 or prev_tick is None:
                start_tick = tick

            elif prev_tick is not None and (
                tick != prev_tick + 1 or t == len(track_ticks)
            ):
                # The end of a static segment

                if len(segment_norms) == 1:
                    continue

                end_tick = prev_tick
                avg_norm = np.nanmean(np.array(segment_norms), axis=0)
                start_frame = nonnull_movelets_df[
                    (nonnull_movelets_df["track_id"] == track_id)
                    & (nonnull_movelets_df["tick"] == start_tick)
                ]["start_frame"].values[0]
                end_frame = nonnull_movelets_df[
                    (nonnull_movelets_df["track_id"] == track_id)
                    & (nonnull_movelets_df["tick"] == end_tick)
                ]["end_frame"].values[0]

                start_timecode = nonnull_movelets_df[
                    (nonnull_movelets_df["track_id"] == track_id)
                    & (nonnull_movelets_df["tick"] == start_tick)
                ]["start_timecode"].values[0]
                end_timecode = nonnull_movelets_df[
                    (nonnull_movelets_df["track_id"] == track_id)
                    & (nonnull_movelets_df["tick"] == end_tick)
                ]["end_timecode"].values[0]

                try:
                    movement = compute_movement(
                        end_timecode - start_timecode,
                        segment_norms[0],
                        segment_norms[len(segment_norms) - 1],
                    )[0]
                except Exception as ex:
                    print(ex)
                    print(
                        end_timecode - start_timecode,
                        len(segment_norms),
                        segment_norms[0],
                        segment_norms[len(segment_norms) - 1],
                    )
                    continue

                static_movelets.append(
                    {
                        "static_pose_id": static_pose_id,
                        "track_id": track_id,
                        "start_frame": start_frame,
                        "end_frame": end_frame,
                        "norm": avg_norm,
                        "movement": movement,
                    }
                )
                static_pose_id += 1
                start_tick = tick
                end_tick = None
                segment_norms = []

            if t < len(track_ticks):
                this_norm = nonnull_movelets_df[
                    (nonnull_movelets_df["track_id"] == track_id)
                    & (nonnull_movelets_df["tick"] == tick)
                ]["norm"].values[0]
                this_norm[this_norm == -1] = np.nan
                segment_norms.append(this_norm)
                prev_tick = tick

    # Create PosePlot (PixPlot) inputs

    images_dir = f"{OUTPUT_PATH}/input/{video_name}/pose_images"
    if not os.path.isdir(images_dir):
        os.makedirs(images_dir)
    img_metadata_fp = open(
        f"{OUTPUT_PATH}/input/{video_name}/{video_name}.csv",
        "w",
        newline="",
        encoding="utf-8",
    )
    img_metadata_file = csv.writer(img_metadata_fp)

    # PixPlot metadata elements:
    # year is an integer but doesn't need to be a year
    # label can be the cluster the pose is in
    # description is plain text
    # can also supply any number of "tags", but it's not clear how these would be useful
    img_metadata_file.writerow(["filename", "description", "year"])

    features_dir = f"{OUTPUT_PATH}/input/{video_name}/pose_features"
    if not os.path.isdir(features_dir):
        os.makedirs(features_dir)

    for movelet in static_movelets:
        print(
            "looking for match between frame",
            movelet["start_frame"],
            movelet["end_frame"],
            "track ID",
            movelet["track_id"],
        )

        # Prefer a target frame in the middle of the movelet, but if the actual pose index
        # is missing from this frame (which can happen sometimes), just use the first frame
        # of the movelet
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
        except Exception as e:
            print(
                "Couldn't find representative pose from movelet middle or beginning, skipping"
            )
            continue

        save_name = f"{images_dir}/{target_frame}_{target_pose['pose_idx']}.jpg"

        if not os.path.isfile(save_name):
            bbox = [round(v) for v in target_pose["bbox"]]

            frame_faces = await db.get_frame_faces(video_id, target_frame)

            if len(frame_faces):
                faces_df = pd.DataFrame.from_records(
                    frame_faces, columns=frame_faces[0].keys()
                )

                target_face = faces_df[faces_df["pose_idx"] == target_pose["pose_idx"]]
                if len(target_face):
                    target_face_df = target_face.iloc[0]
                    face_bbox = [round(v) for v in target_face_df["bbox"]]

                    min_x = min(bbox[0], face_bbox[0])
                    min_y = min(bbox[1], face_bbox[1])
                    max_x = max(bbox[0] + bbox[2], face_bbox[0] + face_bbox[2])
                    max_y = max(bbox[1] + bbox[3], face_bbox[1] + face_bbox[3])
                    b_w = max_x - min_x
                    b_h = max_y - min_y

                    # A bbox that includes the body and the face (if detected)
                    bbox = [min_x, min_y, b_w, b_h]

            pose_frame_image = iio.imread(
                f"/videos/{video_name}", index=target_frame - 1, plugin="pyav"
            )

            pose_img = Image.fromarray(pose_frame_image)

            img_size = pose_img.size

            pose_img = pose_img.resize((img_size[0] * UPSCALE, img_size[1] * UPSCALE))
            drawing = ImageDraw.Draw(pose_img)
            keypoints_triples = [
                (
                    target_pose["keypoints"][i],
                    target_pose["keypoints"][i + 1],
                    target_pose["keypoints"][i + 2],
                )
                for i in range(0, len(target_pose["keypoints"]), 3)
            ]
            drawing = draw_armatures(keypoints_triples, drawing)

            pose_img = pose_img.resize(
                (img_size[0], img_size[1]), resample=Image.Resampling.LANCZOS
            )

            cropped_pose_frame_image = pose_img.crop(
                [bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]]
            )

            img = cropped_pose_frame_image

            print("saving image", save_name)
            img.save(save_name)

            cropped_pose_frame_image.close()
            pose_img.close()

            # Assumes there's always a features file if there's an image file
            pose_features = np.nan_to_num(movelet["norm"], nan=-1)
            np.save(
                f"{features_dir}/{target_frame}_{target_pose['pose_idx']}.npy",
                pose_features,
            )

            img.close()

        frame_minute = round(target_frame / video_fps / 60)

        img_metadata_file.writerow(
            [
                f"{target_frame}_{target_pose['pose_idx']}.jpg",
                f"Frame {target_frame} | pose {target_pose['pose_idx']} | track {target_pose['track_id']}",
                str(frame_minute),
            ]
        )

    img_metadata_fp.close()

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
