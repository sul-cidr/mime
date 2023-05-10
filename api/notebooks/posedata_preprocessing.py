from datetime import datetime, timedelta
import json
import math
import os
from pathlib import Path
import statistics

import cv2
from IPython.display import display
from ipywidgets import IntProgress
import jsonlines
import numpy as np
from skimage.metrics import structural_similarity

from yolox.tracker.byte_tracker import BYTETracker

SEEK_SCORE_THRESHOLD = 0.99


def get_available_videos(data_folder):
    """
    XXX CURRENTLY NOT USED
    Available videos will be limited to those with a .json and matching video (.mp4, .avi, etc)
    file in a predefined directory (defaulting to the notebook's running directory).
    NOTE that this is currently not being used, as the ipyfilechooser widget provides
    sufficient filtering abilities.
    """
    available_json_files = list(data_folder.glob("*.json"))
    available_video_files = (
        p.resolve()
        for p in Path(data_folder).glob("*")
        if p.suffix in {".avi", ".mp4", ".mov", ".mkv", ".webm"}
    )
    available_json = [
        json_file.stem.split(".")[0] for json_file in available_json_files
    ]

    available_videos = []

    for video_name in available_video_files:
        if video_name.stem.split(".")[0] in available_json:
            available_videos.append(video_name.name)

    return available_videos


def check_video_seekability(video_file, viz=False, frame_interval=1000):
    """
    Compare video frames extracted via OpenCV when reading the entire video
    sequentially (as is done by OpenPifPaf and probably other pose estimation
    libraries) vs seeking to a specific play point and reading a frame (which
    is what our visualization methods do at present), sampling across the
    entire video and averaging the results. It seems that dodgy video encoding
    can cause these frames to differ by up to several seconds, leading to a
    mismatch between detected poses and the background images used to visualize
    the detections. A basic structural features comparison seems to suffice.
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


# --- POSE TRACKING FUNCTIONS ---

# This can be run as a separate preprocessing/data ingest step,
# as it only relies on the data in the Open PifPaf detection output
# JSON. It is used to generate an augmented version of the JSON, the
# only difference being that detected poses that ByteTrack was able
# to track across multiple frames are given consistent tracking IDs.


class TrackerArgs:
    """Default arguments to use when instantiating a BYTETracker"""

    def __init__(self):
        self.track_thresh = 0.5  # min pose score for tracking -- may need to lower this
        self.track_buffer = 30
        self.match_thresh = 0.8
        self.aspect_ratio_thresh = 1.6
        self.min_box_area = 10
        self.mot20 = False


def track_poses(pose_data, video_fps, video_width, video_height, show_progress=False):
    """
    Use a BYTETracker to detect consecutive pose 'tracklets' in the precomputed
    pose_data input (e.g., per-frame detections from Open PifPaf) that likely
    belong to the same figure, and write this tracking information into a new
    copy of pose_data
    """
    args = TrackerArgs()
    tracker = BYTETracker(args, frame_rate=video_fps)

    tracking_results = []
    tracking_ids = set()

    print("Tracking detected figures in pose data")

    if show_progress:
        tracking_bar = IntProgress(min=0, max=len(pose_data))
        display(tracking_bar)

    for f, frame in enumerate(pose_data):
        if show_progress and (f % 100 == 0):
            tracking_bar.value = f

        frameno = (
            frame["frame"] - 1
        )  # This should always  bethe 0-based index of the frame
        detections = []
        for prediction in frame["predictions"]:
            # Need to convert prediction["bbox"] to the format BYTETracker expects
            # and package these into detections
            # Detection format is
            # np.array([[x1, y1, x2, y2, score] ... for all pose bboxes in frame ]) (dtype?)
            # Actually it looks like this when it comes out of the CPU detector:
            # tensor([[ 8.0524e+02,  2.1848e+02,  9.5338e+02,  5.8879e+02,  9.9535e-01,
            #  9.1142e-01,  0.0000e+00], ...
            # but then it gets converted to
            # bboxes: [[  814.2597     224.75363    966.6578     561.90466 ] ...
            # scores: [0.9205966 ...
            # BYTETracker wants predictions that go minx, miny, maxx, maxy, which it then
            # immediately converts (back) to minx, miny, width, height, with some added
            # FPU noise :-(
            bbox = [
                prediction["bbox"][0],
                prediction["bbox"][1],
                prediction["bbox"][0] + prediction["bbox"][2],
                prediction["bbox"][1] + prediction["bbox"][3],
            ]
            detections.append(bbox + [prediction["score"]])
        # Args 2 and 3 can differ if the image has been scaled at some point, which we're not doing
        if len(detections) > 0:
            online_targets = tracker.update(
                np.array(detections, dtype=float),
                [video_height, video_width],
                (video_height, video_width),
            )
            for t in online_targets:
                tlwh = t.tlwh
                tid = t.track_id
                vertical = tlwh[2] / tlwh[3] > args.aspect_ratio_thresh
                if tlwh[2] * tlwh[3] > args.min_box_area and not vertical:
                    tracking_ids.add(tid)
                    tracking_results.append(
                        [
                            frameno,
                            tid,
                            round(tlwh[0], 2),
                            round(tlwh[1], 2),
                            round(tlwh[2], 2),
                            round(tlwh[3], 2),
                            round(t.score, 2),
                        ]
                    )

    if show_progress:
        tracking_bar.bar_style = "success"

    tracking_matches = 0

    min_tracking_id = min(tracking_ids)

    # Merge tracking results with pose data
    tracked_pose_data = pose_data.copy()

    print("Merging tracking data with existing pose data")

    if show_progress:
        merging_bar = IntProgress(min=0, max=len(tracking_results))
        display(merging_bar)

    for r, res in enumerate(tracking_results):
        if show_progress and (r % 1000 == 0):
            merging_bar.value = r

        res_bbox = [res[2], res[3], res[4], res[5]]
        frameno = res[0]
        matched_predictions = []
        # The bbox coordinates returned by the ByteTracker usually deviate by a small
        # amount from those it receives as input. Perhaps they're being smoothed/
        # interpolated as part of the tracking process? in any case, this complicates
        # the matching process. Fortunately, the ByteTracker doesn't ever seem to modify
        # the pose confidence scores, so we match on those first, then if there's a tie,
        # we choose the bbox with the smallest Euclidean distance from the tracker's bbox.
        for poseno, prediction in enumerate(pose_data[frameno]["predictions"]):
            if res[6] == round(prediction["score"], 2):
                matched_predictions.append(
                    {"poseno": poseno, "bbox": prediction["bbox"]}
                )
        match_poseno = None
        if len(matched_predictions) == 1:
            match_poseno = matched_predictions[0]["poseno"]
        elif len(matched_predictions) > 1:
            match_distances = {}
            for matched_pred in matched_predictions:
                match_distances[matched_pred["poseno"]] = math.dist(
                    matched_pred["bbox"], res_bbox
                )
            match_poseno = min(match_distances, key=match_distances.get)
        if match_poseno is not None:
            tracked_pose_data[frameno]["predictions"][match_poseno]["tracking_id"] = (
                res[1] - min_tracking_id + 1
            )
            # ? Use ByteTrack's bbox instead of the original Open PifPaf bbox in the
            # hopes that it will smooth over single-frame aberrations better
            tracked_pose_data[frameno]["predictions"][match_poseno]["bbox"] = res_bbox
            tracking_matches += 1

    if show_progress:
        merging_bar.bar_style = "success"

    print("Tracked", tracking_matches, "poses across all frames")
    print("Total entities tracked:", len(tracking_ids))

    return tracked_pose_data


def count_tracked_poses(tracked_pose_data):
    """
    Get the number of figures currently being tracked in each
    frame and write them to a list, which can then be added
    to pose_series for use in the Bokeh timeline vis.
    """
    tracked_poses_counts = []

    for frame in tracked_pose_data:
        tracked_poses_in_frame = 0
        for prediction in frame["predictions"]:
            if "tracking_id" in prediction:
                tracked_poses_in_frame += 1

        tracked_poses_counts.append(tracked_poses_in_frame)

    return tracked_poses_counts


def get_pose_tracking(video_file, pose_data, video_fps, video_width, video_height):
    """
    If previously computed pose tracking data is not available in a file,
    run track_poses() to generate it. Also build and return a tracked_poses
    data structure that maps tracklet IDs to the frames in which they appear.
    """

    data_dir = Path(video_file).with_suffix("")

    tracked_pose_file = Path(
        data_dir, Path(f"{video_file}.tracked.openpifpaf.json").name
    )

    if os.path.isfile(tracked_pose_file):
        print("Loading previously computed pose tracking information")
        tracked_pose_data = json.load(open(tracked_pose_file, "r", encoding="utf8"))
    else:
        tracked_pose_data = track_poses(
            pose_data, video_fps, video_width, video_height, show_progress=True
        )
        print("Writing pose data with tracking info to", tracked_pose_file)
        json.dump(tracked_pose_data, open(tracked_pose_file, "w", encoding="utf8"))

    pose_tracks = {}

    tracked_poses = count_tracked_poses(
        tracked_pose_data,
    )

    for frameno, frame in enumerate(tracked_pose_data):
        for poseno, pose_prediction in enumerate(frame["predictions"]):
            if "tracking_id" in pose_prediction:
                tracking_id = pose_prediction["tracking_id"]
                if tracking_id in pose_tracks:
                    pose_tracks[tracking_id].append(
                        {"frameno": frameno, "poseno": poseno}
                    )
                else:
                    pose_tracks[tracking_id] = [{"frameno": frameno, "poseno": poseno}]

    return [tracked_pose_data, pose_tracks, tracked_poses]
