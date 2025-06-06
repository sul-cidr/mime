#!/usr/bin/env python3

"""CLI to add hand detection data to pose data for a video in the db."""

import argparse
import asyncio
import logging
import math
from pathlib import Path

import jsonlines
import numpy as np
import tensorflow as tf
from rich.logging import RichHandler

from lib.pose_utils import HAND_21_ANGLES
from mime_db import MimeDb

BATCH_SIZE = 1000

model_path = "lib/hands/keypoint_classifier.hdf5"


def get_segment_midpoint_3d(seg1, seg2):
    return [seg1[0] + seg2[0], seg1[1] + seg2[1], seg1[2] + seg2[2]]


# Trying this from https://www.mathworks.com/matlabcentral/answers/445994-how-to-calculate-a-rotation-matrix-between-two-3d-points
def derive_rotation_matrix(p0, p1):
    C = np.cross(p0, p1)
    D = np.dot(p0, p1)
    NP0 = np.linalg.norm(p0)

    Z = [[0, -C[2], C[1]], [C[2], 0, -C[0]], [-C[1], C[0], 0]]
    R = (
        np.eye(3)
        + Z
        + np.square(Z) * (1 - D) / np.square(np.linalg.norm(C)) / np.square(NP0)
    )

    # A simpler case that doesn't seem to apply here
    # R = np.sign(D) * (np.linalg.norm(p1) / NP0)

    return R


def project_hand_keypoints(hand, pose):
    """PHALP provides body keypoints in 3D in a local context, albeit from the
    perspective of the camera, if the camera that took the original 2D image
    were "zoomed in" on the pose. These are stored as 13 x 3 COCO keypoints
    (flat) in pose.keypoints3d in the DB.
    PHALP also has a "global_orient" matrix transform that rotates the
    3d_joints so that the plane formed by the hips and ankles is aligned
    with the X,Y axis (and perpendicular to the Z axis), basically facing the
    "close-up" camera. The transform is not saved into the DB, but the field
    pose.global3d_coco13 includes the transformed version, so presumably the
    transform can be derived from them.
    Finally, PHALP provides an [X,Y,Z] "camera" 3D transform that can be used to
    project the raw pose.keypoints3d into a 3D scene that includes the estimated
    camera position (greatly increasing the depth of the space).

    WiLoR's keypoints3d output provides the hand keypoints in 3D, in a
    seemingly arbitrary orientation. These coordinates can be summed with the
    first row of WiLoR's global_orient matrix (its "global" apparently has a
    different meaning than PHALP's) to rotate the hand to appear from the
    perspective of the camera that took the 2D iamge, as if the camera were
    immediately in front of the hand.
    WiLoR also provides a camera transform and estimated camera position
    that can be used to project the hand coordinates into the estimated 3D scene,
    but we don't use this for the Scene3D viz; instead we just match the raw 3D
    hand coords + the hand global_orient vector (getting the hand into the
    "viewed from camera" orientation) to the nearest pose's wrist, then shift
    the hand coords to align with the pose's wrists in the 3D scene projection.

    How to project the hand coords into the same "global" context as the
    3D pose?
    Probably the simplest approach is similar to the Scene3D manipulations:
    - project the pose into the camera scene
    - add the raw hand coords to the hand's global_orient vector to rotate the
      hand so that it is viewed from the camera's perspective
    - shift the hand coords so the wrist point matches the projected pose's
    - "de-project" the hand coords by applying the inverse of the pose camera
      transform
    - apply the pose's "global_orient" transform to get the "global" hand
      coords
    """

    pose_kpts_3d = unflatten_triplets(pose["keypoints3d"])
    pose_global_3d = unflatten_triplets(pose["global3d_coco13"])

    # Project the pose into the camera space
    pose_proj = [
        [p[0] + pose["camera"][0], p[1] + pose["camera"][1], p[2] + pose["camera"][2]]
        for p in pose_kpts_3d
    ]

    # hand_rot = np.matmul(hand["kpts_3d"], hand["global_orient"])

    # Rotate the 3D hand so that it appears from the angle in the orig 2D image
    hand_rot = [
        [
            h[0] + hand["global_orient"][0][0],
            h[1] + hand["global_orient"][0][1],
            h[2] + hand["global_orient"][0][2],
        ]
        for h in hand["kpts_3d"]
    ]

    # Get the wrist coordinates of the rotated hand
    hand_base = hand_rot[0]

    # Get the wrist coordinates of the correct hand of the projected pose
    if hand["right"]:
        pose_wrist_coords = pose_proj[6]
    else:
        pose_wrist_coords = pose_proj[5]

    # Express the rotated hand coordinates relative to the base of the hand's wrist
    hand_zeroed = [
        [trio[0] - hand_base[0], trio[1] - hand_base[1], trio[2] - hand_base[2]]
        for trio in hand_rot
    ]

    # Translate the wrist-origin rotated hand coords to the pose's wrist
    hand_trans = [
        [
            trio[0] + pose_wrist_coords[0],
            trio[1] + pose_wrist_coords[1],
            trio[2] + pose_wrist_coords[2],
        ]
        for trio in hand_zeroed
    ]

    # "Deproject" the hand coordinates (now in the pose's reference frame)
    # so the camera is not a factor.
    hand_deproj = [
        [
            trio[0] - pose["camera"][0],
            trio[1] - pose["camera"][1],
            trio[2] - pose["camera"][2],
        ]
        for trio in hand_trans
    ]

    # Finally, need to apply the same transform to the pose-referenced hand
    # coordinates that was applied to get the pose coordinates (keypoints3d)
    # into the de-rotated/"squared up" representation.
    pose_global_xform = derive_rotation_matrix(pose_kpts_3d[0], pose_global_3d[0])

    hand_global = np.matmul(hand_deproj, pose_global_xform).flatten()

    # hand_global = np.array(hand_deproj).flatten()

    return hand_global


# Derived from https://github.com/Kazuhito00/hand-gesture-recognition-using-mediapipe
def get_class_weights(keypoints_2d, model):
    # Coords need to be shifted relative to point 0 (wrist) and normalized
    wrist_coords = [keypoints_2d[0], keypoints_2d[1]]
    shifted_coords = []
    for i in range(0, len(keypoints_2d), 2):
        shifted_coords.extend(
            [keypoints_2d[i] - wrist_coords[0], keypoints_2d[i + 1] - wrist_coords[1]]
        )

    abs_val = max([abs(val) for val in shifted_coords])
    normed_coords = [val / abs_val for val in shifted_coords]

    predict_result = model.predict(np.array([normed_coords]), verbose=0)

    return np.squeeze(predict_result)


# Inspired by https://www.geeksforgeeks.org/angle-between-a-pair-of-lines-in-3d/
def calculate_angle_in_3d(arm1, vertex, arm2):
    x1, y1, z1 = arm1
    x2, y2, z2 = vertex
    x3, y3, z3 = arm2

    # Find direction ratio of line AB
    ABx = x1 - x2
    ABy = y1 - y2
    ABz = z1 - z2

    # Find direction ratio of line BC
    BCx = x3 - x2
    BCy = y3 - y2
    BCz = z3 - z2

    # Find magnitudes of lines AB and BC
    magnitude_AB = ABx * ABx + ABy * ABy + ABz * ABz
    magnitude_BC = BCx * BCx + BCy * BCy + BCz * BCz

    # Find the cosine of the angle formed by lines AB and BC
    magnitude = magnitude_AB * magnitude_BC

    if magnitude == 0:
        return 0

    # Find the dot product of lines AB & BC
    dot_product = ABx * BCx + ABy * BCy + ABz * BCz

    angle = dot_product / math.sqrt(magnitude_AB * magnitude_BC)

    # Get the angle in radians
    angle = (angle * 180) / 3.14

    return round(abs(angle), 4)


def triplets_to_pairs(kpts):
    # Convert a flattened vector of [x1, y1, c1, x2, y2, c2, ...] to [[x1, y1], [x2, y2], ...]
    return [[k[0], k[1]] for k in np.array_split(kpts, len(kpts) / 3)]


def unflatten_triplets(kpts):
    return [[k[0], k[1], k[2]] for k in np.array_split(kpts, len(kpts) / 3)]


def xywh_to_xyxy(bbox):
    # Convert xmin, ymin, width, height bbox to xmin, ymin, xmax, ymax
    return [bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]]


def get_2d_xyxy(points_list):
    # Extract xyxy bbox from a list of 2d keypoints
    points = np.array(points_list)

    xmin = min(points[:, 0])
    ymin = min(points[:, 1])
    xmax = max(points[:, 0])
    ymax = max(points[:, 1])

    return [xmin, ymin, xmax, ymax]


def extend_2d_xyxy(points, extend=0):
    # Expand an xyxy bbox by some multiple of the height and width
    xmin, ymin, xmax, ymax = points

    width = xmax - xmin
    height = ymax - ymin

    return [
        xmin - (width * extend),
        ymin - (height * extend),
        xmax + (width * extend),
        ymax + (height * extend),
    ]


def get_extend_2d_xyxy(points, extend=0.2):
    # Obtain an xyxy bbox from a list of points and expand it by some fraction of width and height
    return extend_2d_xyxy(get_2d_xyxy(points), extend)


def get_hand_center(hand):
    # Find the center point of a hand's 2D bounding box
    xmin, ymin, xmax, ymax = get_2d_xyxy(hand)

    return np.array([(xmax + xmin) / 2, (ymax + ymin) / 2])


def do_xyxys_overlap(xyxy1, xyxy2):
    # Check if two xyxy bounding boxes overlap
    return not (
        xyxy1[2] < xyxy2[0]
        or xyxy1[0] > xyxy2[2]
        or xyxy1[3] < xyxy2[1]
        or xyxy1[1] > xyxy2[3]
    )


async def match_hands_in_frames(
    video_id, hands_to_match, min_frameno, max_frameno, db, model
):
    """Hands are matched to poses based on the distance of each detected
    hand's wrist (base) from each pose's wrist, considering only right wrists
    if the hand is estimated to be a right hand, etc. Matches are calculated
    based upon 2D image coordinates only, which is not ideal when hands overlap,
    but matching in 3D seems unlikely to work better given that the body and
    hands keypoints are derived from different models whose depth estimation
    results may vary widely."""

    logging.info(f"Matching hands in frame {min_frameno} to {max_frameno}")

    matched_hands = 0
    duplicate_hands = 0
    rejected_matches = 0

    matches_to_assign = []

    frame_poses = await db.get_frame_data_range(video_id, min_frameno, max_frameno)

    poses_by_frame = {}
    for pose in frame_poses:
        if pose["frame"] in poses_by_frame:
            poses_by_frame[pose["frame"]].append(pose)
        else:
            poses_by_frame[pose["frame"]] = [pose]

    for frameno in hands_to_match:
        if frameno not in poses_by_frame:
            continue
        frame_hands = hands_to_match[frameno]
        frame_poses = poses_by_frame[frameno]

        pose_to_hands = {}

        for h, hand in enumerate(frame_hands):
            hand_base = hand["kpts_2d"][0]

            closest_dist = -1
            best_pose_match = -1

            is_right = hand["right"] == 1

            for p, pose in enumerate(frame_poses):
                # Skip non-tracked poses
                if pose["track_id"] == 0:
                    continue

                # Match each left/right hand to the closest left/right wrist
                if is_right is True:
                    target_wrist = triplets_to_pairs(pose["keypoints"])[6]
                else:
                    target_wrist = triplets_to_pairs(pose["keypoints"])[5]

                # wrist_hand_dist = np.linalg.norm(target_wrist - hand_center)
                wrist_hand_dist = np.linalg.norm(
                    np.array(target_wrist) - np.array(hand_base)
                )

                if closest_dist >= 0 and closest_dist < wrist_hand_dist:
                    continue
                else:
                    closest_dist = wrist_hand_dist
                    best_pose_match = p

            # If the hand's bbox doesn't overlap with the pose at all, ignore it
            expanded_pose_xyxy = extend_2d_xyxy(
                xywh_to_xyxy(frame_poses[best_pose_match]["bbox"])
            )
            expanded_hand_xyxy = get_extend_2d_xyxy(hand["kpts_2d"])

            if not do_xyxys_overlap(expanded_pose_xyxy, expanded_hand_xyxy):
                rejected_matches += 1
                continue

            # Sometimes there are multiple detections of the same hand, so
            # if a pose has already been assigned a right or left hand and a
            # new match is found for it, ignore the new match.
            if best_pose_match in pose_to_hands:
                if is_right in pose_to_hands[best_pose_match]:
                    duplicate_hands += 1
                    continue
                else:
                    pose_to_hands[best_pose_match][is_right] = h
            else:
                pose_to_hands[best_pose_match] = {is_right: h}

            if "confidence" in hand:
                confidence = hand["confidence"]
            else:
                confidence = 1

            if "bbox" in hand:
                bbox = hand["bbox"]
            else:
                bbox = get_2d_xyxy(hand["kpts_2d"])

            # Flatten arrays of coordinates into flat vectors for DB ingest
            kpts_2d = [coord for pair in hand["kpts_2d"] for coord in pair]
            kpts_3d = [coord for triplet in hand["kpts_3d"] for coord in triplet]
            global_orient = [
                coord for triplet in hand["global_orient"] for coord in triplet
            ]

            # Get the rectified/global hand coordinates in the pose's frame of reference
            projected_hand_keypoints = project_hand_keypoints(
                hand, frame_poses[best_pose_match]
            )

            # Calculate angles between hand joints
            joint_angles_3d = [
                calculate_angle_in_3d(
                    hand["kpts_3d"][triad[0]],
                    hand["kpts_3d"][triad[1]],
                    hand["kpts_3d"][triad[2]],
                )
                for triad in HAND_21_ANGLES
            ]

            # Get the logits (linear class scores) from a hand gesture classification model
            class_weights = get_class_weights(kpts_2d, model)

            matched_hands += 1

            matches_to_assign.append(
                [
                    video_id,
                    frameno,
                    frame_poses[best_pose_match]["pose_idx"],
                    hand["personid"],
                    bbox,
                    is_right,
                    confidence,
                    hand["pred_cam"],
                    hand["cam_t"],
                    kpts_2d,
                    kpts_3d,
                    joint_angles_3d,
                    class_weights,
                    projected_hand_keypoints,
                    global_orient,
                    frame_poses[best_pose_match]["track_id"],
                ]
            )

    if len(matches_to_assign) > 0:
        await db.add_pose_hands(matches_to_assign)

    logging.info(f"Duplicate hand-to-pose matches (rejected): {duplicate_hands}")
    logging.info(
        f"Rejected based upon lack of overlapping bounding boxes: {rejected_matches}"
    )


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

    hands_file = Path(f"{args.video_name}.hands.WiLoR.jsonl")

    video_name = Path(args.video_name)

    # Connect to the database
    db = await MimeDb.create()

    # Get video metadata
    video_name = video_name.name
    video_id = await db.get_video_id(video_name)

    # Only consider frames with tracked poses in them
    track_frame_records = await db.get_track_frames(video_id)

    track_frame_ids = {frame_record["frame"] for frame_record in track_frame_records}

    hands_to_match = {}
    min_frameno = None
    max_frameno = None

    logging.info("Loading classification model")
    model = tf.keras.models.load_model(model_path, compile=False)

    # Consider getting the linear weights of the categories to use as embeddings,
    # rather than running softmax to get their probabilities
    model.layers[-1].activation = tf.keras.activations.linear

    logging.info("Matching tracked poses to hands detected in video")

    with jsonlines.open(hands_file) as reader:
        for hand in reader:
            if ("confidence" in hand and hand["confidence"] == 0) or hand[
                "frame"
            ] not in track_frame_ids:
                continue

            if hand["frame"] in hands_to_match:
                hands_to_match[hand["frame"]].append(hand)
            else:
                hands_to_match[hand["frame"]] = [hand]

            if min_frameno is None:
                min_frameno = hand["frame"]
            else:
                min_frameno = min(min_frameno, hand["frame"])

            if max_frameno is None:
                max_frameno = hand["frame"]
            else:
                max_frameno = max(max_frameno, hand["frame"])

            if len(hands_to_match) >= BATCH_SIZE:
                await match_hands_in_frames(
                    video_id, hands_to_match, min_frameno, max_frameno, db, model
                )
                hands_to_match = {}
                min_frameno = None
                max_frameno = None

        if len(hands_to_match) > 0:
            await match_hands_in_frames(
                video_id, hands_to_match, min_frameno, max_frameno, db, model
            )

    await db.index_pose_hands()


if __name__ == "__main__":
    asyncio.run(main())
