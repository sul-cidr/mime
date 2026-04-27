import json
import math
import os
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import jsonlines
import numpy as np
from IPython.display import display
from ipywidgets import IntProgress
from skimage.metrics import structural_similarity

sys.path.append("..")

SEEK_SCORE_THRESHOLD = 0.99



def check_video_seekability(video_file, viz=False, frame_interval=1000):
    """
    Compare video frames extracted via OpenCV when reading the entire video
    sequentially (as is done by many inference libraries) vs seeking to a
    specific play point and reading a frame (which is what our visualization
    methods do at present), sampling across the entire video and averaging the
    results. It seems that dodgy video encoding can cause these frames to differ
    by up to several seconds, leading to a mismatch between detected poses and
    the background images used to visualize the detections. A basic structural
    features comparison seems to suffice.
    Videos with less than a 99% match rate should probably be re-encoded and
    the pose estimation re-run on them before adding them to the posedata
    corpus for study.
    """
    read_cap = cv2.VideoCapture(video_file)
    seek_cap = cv2.VideoCapture(video_file)
    video_length = int(seek_cap.get(cv2.CAP_PROP_FRAME_COUNT))

    sim_frames = []
    sim_values = []

    print(
        "Comparing sequential read and seeked frames to verify video encoding quality"
    )
    progress_bar = IntProgress(min=0, max=video_length)
    display(progress_bar)

    for frame_i in range(video_length):
        ret, read_frame = read_cap.read()
        if frame_i % frame_interval == 0:
            progress_bar.value = frame_i
            seek_cap.set(1, frame_i)
            ret, seek_frame = seek_cap.read()

            read_image = cv2.cvtColor(read_frame, cv2.COLOR_BGR2GRAY)
            seek_image = cv2.cvtColor(seek_frame, cv2.COLOR_BGR2GRAY)

            score, diff = structural_similarity(read_image, seek_image, full=True)
            sim_frames.append(frame_i)
            sim_values.append(score)

    read_cap.release()
    seek_cap.release()

    if viz is True:
        import matplotlib.pyplot as plt
        plt.plot(sim_frames, sim_values, label=f"seek/play sim")
        plt.title(f"{video_file.split('/')[-1]}")
        plt.ylim(0, 1.1)
        plt.xlabel(f"sampled every {frame_interval} frames")
        plt.legend(loc="upper left")
        plt.show()

    return statistics.mean(sim_values)


def preprocess_pose_json(pose_file, video_file):
    """
    Parse the JSON pose estimation output file and cross-reference it
    with the actual source video file to build two data structures:
    - pose_data: per-frame information about all pose armatures detected
    - pose_series: numerous lists, all of total_frames length, providing
      different data about each frame, for use in the Bokeh explorer UI
    """
    pose_json = jsonlines.open(pose_file)

    cap = cv2.VideoCapture(video_file)
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    # video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    # video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    pose_data = []

    # Per-frame pose data: frame, seconds, num_poses, avg_pose_conf, avg_coords_per_pose
    pose_series = {
        "frame": [],
        "seconds": [],
        "timestamp": [],
        "num_poses": [],
        "avg_score": [],
        "avg_coords_per_pose": [],
    }

    for frame in pose_json:
        pose_data.append(frame)

        # Frame output is numbered from 1 in the JSON
        seconds = float(frame["frame"] - 1) / video_fps

        num_poses = len(frame["predictions"])
        pose_series["num_poses"].append(num_poses)

        pose_series["frame"].append(frame["frame"] - 1)
        pose_series["seconds"].append(seconds)

        # Construct a timestamp that can be used with Bokeh's DatetimeTickFormatter
        td = timedelta(seconds=seconds)
        datestring = str(td)
        if td.microseconds == 0:
            datestring += ".000000"
        dt = datetime.strptime(datestring, "%H:%M:%S.%f")

        pose_series["timestamp"].append(dt)

        pose_scores = []
        pose_coords_counts = []
        avg_score = 0  # NaN for empty frames?
        avg_coords_per_pose = 0

        for pose in frame["predictions"]:
            pose_scores.append(pose["score"])
            pose_coords = 0
            for i in range(0, len(pose["keypoints"]), 3):
                if pose["keypoints"][i + 2] != 0:
                    pose_coords += 1

            # To find the typically small proportion of poses that are complete
            # if pose_coords == 17:
            #     print(frame['frame'])

            pose_coords_counts.append(pose_coords)

        if num_poses > 0:
            avg_score = sum(pose_scores) / num_poses
            avg_coords_per_pose = sum(pose_coords_counts) / num_poses

        pose_series["avg_score"].append(avg_score)
        pose_series["avg_coords_per_pose"].append(avg_coords_per_pose)

    return [pose_data, pose_series]