import logging
import math

import numpy as np

from .yolox.tracker.byte_tracker import BYTETracker


class TrackerArgs:
    """Default arguments to use when instantiating a BYTETracker"""

    def __init__(self):
        self.track_thresh = 0.5  # min pose score for tracking -- lower this?
        self.track_buffer = 30
        self.match_thresh = 0.8
        self.aspect_ratio_thresh = 1.6
        self.min_box_area = 10
        self.mot20 = False


def track_poses(pose_data, video_fps, video_width, video_height):
    """
    Use a BYTETracker to detect consecutive pose 'tracklets' in the precomputed
    pose_data input (e.g., per-frame detections from Open PifPaf) that likely
    belong to the same figure
    """
    args = TrackerArgs()

    tracker = BYTETracker(args, frame_rate=video_fps)

    logging.info("Tracking detected figures in pose data")

    tracking_results = []
    tracking_ids = set()
    frame_poses = {}
    prev_frame = -1
    detections = []

    # ! pose_data MUST be ordered by frame number
    # (or we could just re-sort them here)
    for pose in pose_data:
        frameno = pose["frame"]
        if frameno > prev_frame:
            # Args 2 and 3 can differ if the image has been scaled at some
            # point, but we don't do that
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
            detections = []
            prev_frame = frameno
            frame_poses[frameno] = []

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
            pose["bbox"][0],
            pose["bbox"][1],
            pose["bbox"][0] + pose["bbox"][2],
            pose["bbox"][1] + pose["bbox"][3],
        ]
        detections.append(bbox + [pose["score"]])
        if frameno not in frame_poses:
            frame_poses[frameno] = [pose]
        else:
            frame_poses[frameno].append(pose)

    tracking_matches = 0

    min_tracking_id = min(tracking_ids)

    # Align tracking results with pose data

    track_data = []

    logging.info("Aligning tracking data with existing pose data")

    for res in tracking_results:
        res_bbox = [res[2], res[3], res[4], res[5]]
        frameno = res[0]
        # The bbox coordinates returned by the ByteTracker usually deviate by a small
        # amount from those it receives as input. Perhaps they're being smoothed/
        # interpolated as part of the tracking process? In any case, this complicates
        # the matching process.
        # One approach is to match on the pose confidence scores, since ByteTracker
        # just seems to pass those through unmodified. But it's better just to
        # compute the Euclidean distances between the tracked pose bbox and all of
        # the detected poses in the frame, and choose the one that's closest.
        match_distances = {}
        for matched_pose in frame_poses[frameno]:
            match_distances[matched_pose["pose_idx"]] = math.dist(
                matched_pose["bbox"], res_bbox
            )
        match_poseno = min(match_distances, key=match_distances.get)
        track_data.append(
            {
                "frame": frameno,
                "pose_idx": match_poseno,
                "track_id": res[1] - min_tracking_id + 1,
            }
        )
        tracking_matches += 1

    logging.info(f"Tracked {tracking_matches} poses across all frames")
    logging.info(f"Total entities tracked: {len(tracking_ids)}")

    return track_data
