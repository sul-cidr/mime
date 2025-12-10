import csv
import os
import subprocess

import numpy as np

# Duplicated in api/make_poem_input.py
CSV_HEADERS = [
    "image/width",
    "image/height",
    "image/object/part/NOSE_TIP/center/x",
    "image/object/part/NOSE_TIP/center/y",
    "image/object/part/NOSE_TIP/score",
    "image/object/part/LEFT_SHOULDER/center/x",
    "image/object/part/LEFT_SHOULDER/center/y",
    "image/object/part/LEFT_SHOULDER/score",
    "image/object/part/RIGHT_SHOULDER/center/x",
    "image/object/part/RIGHT_SHOULDER/center/y",
    "image/object/part/RIGHT_SHOULDER/score",
    "image/object/part/LEFT_ELBOW/center/x",
    "image/object/part/LEFT_ELBOW/center/y",
    "image/object/part/LEFT_ELBOW/score",
    "image/object/part/RIGHT_ELBOW/center/x",
    "image/object/part/RIGHT_ELBOW/center/y",
    "image/object/part/RIGHT_ELBOW/score",
    "image/object/part/LEFT_WRIST/center/x",
    "image/object/part/LEFT_WRIST/center/y",
    "image/object/part/LEFT_WRIST/score",
    "image/object/part/RIGHT_WRIST/center/x",
    "image/object/part/RIGHT_WRIST/center/y",
    "image/object/part/RIGHT_WRIST/score",
    "image/object/part/LEFT_HIP/center/x",
    "image/object/part/LEFT_HIP/center/y",
    "image/object/part/LEFT_HIP/score",
    "image/object/part/RIGHT_HIP/center/x",
    "image/object/part/RIGHT_HIP/center/y",
    "image/object/part/RIGHT_HIP/score",
    "image/object/part/LEFT_KNEE/center/x",
    "image/object/part/LEFT_KNEE/center/y",
    "image/object/part/LEFT_KNEE/score",
    "image/object/part/RIGHT_KNEE/center/x",
    "image/object/part/RIGHT_KNEE/center/y",
    "image/object/part/RIGHT_KNEE/score",
    "image/object/part/LEFT_ANKLE/center/x",
    "image/object/part/LEFT_ANKLE/center/y",
    "image/object/part/LEFT_ANKLE/score",
    "image/object/part/RIGHT_ANKLE/center/x",
    "image/object/part/RIGHT_ANKLE/center/y",
    "image/object/part/RIGHT_ANKLE/score",
]

# Default dimension (length, width, maybe depth, eventually) of single pose viz
POSE_MAX_DIM = 100

# This reduces the 45 PHALP coords to 26, just by merging pairs that are very
# close together (e.g., left elbow front and left elbow back)
phalp_to_reduced = [
    [0, 15, 16, 17, 18, 38, 43],
    [1, 37, 40],
    [2, 33],
    [3, 32],
    [4, 31],
    [5, 34],
    [6, 35],
    [7, 36],
    [8, 39],
    [9],
    [10, 26],
    [11, 24],
    [12],
    [13, 29],
    [14, 21],
    [19, 20],
    [21],
    [22, 23],
    [25],
    [27],
    [28],
    [30],
    [36],
    [41],
    [42],
    [44],
]

phalp_to_coco_17 = [
    [0],
    [16],
    [15],
    [18],
    [17],
    [5, 34],
    [2, 33],
    [6, 35],
    [3, 32],
    [7, 36],
    [4, 31],
    [28],
    [27],
    [13, 29],
    [10, 26],
    [14, 30],
    [11, 25],
]

phalp_to_coco_13 = [
    [0],  # Nose
    [5, 34],  # Left shoulder
    [2, 33],  # Right shoulder
    [6, 35],  # Left elbow
    [3, 32],  # Right elbow
    [7, 36],  # Left wrist
    [4, 31],  # Right wrist
    [28],  # Left hip
    [27],  # Right hip
    [13, 29],  # Left knee
    [10, 26],  # Right knee
    [14, 30],  # Left ankle
    [11, 25],  # Right ankle
]

openpifpaf_to_coco_13 = [
    [0],
    [5],
    [6],
    [7],
    [8],
    [9],
    [10],
    [11],
    [12],
    [13],
    [14],
    [15],
    [16],
]


HAND_21_KEYPOINTS = [
    "ulnar_palm",  # 0
    "radial_palm",  # 1
    "thumb_metacarpal",  # 2
    "thumb_proximal",  # 3
    "thumb_distal",  # 4
    "index_metacarpal",  # 5
    "index_proximal",  # 6
    "index_middle",  # 7
    "index_distal",  # 8
    "middle_metacarpal",  # 9
    "middle_proximal",  # 10
    "middle_middle",  # 11
    "middle_distal",  # 12
    "ring_metacarpal",  # 13
    "ring_proximal",  # 14
    "ring_middle",  # 15
    "ring_distal",  # 16
    "pinkie_metacarpal",  # 17
    "pinkie_proximal",  # 18
    "pinkie_middle",  # 19
    "pinkie_distal",  # 20
]


HAND_21_ANGLES = [
    [0, 1, 2],
    [1, 2, 3],
    [2, 3, 4],
    [1, 5, 6],
    [1, 5, 9],
    [2, 1, 5],
    [9, 5, 6],
    [5, 6, 7],
    [6, 7, 8],
    [5, 9, 10],
    [9, 10, 11],
    [10, 11, 12],
    [10, 9, 13],
    [9, 13, 14],
    [13, 14, 15],
    [14, 15, 16],
    [14, 13, 17],
    [13, 17, 18],
    [17, 18, 19],
    [18, 19, 20],
    [13, 17, 0],
]


COCO_13_ANGLES = [
    [1, 0, 2],  # left shoulder - nose - right shoulder
    # [0, 1, 3],
    # [0, 2, 4],
    [0, 1, 7],  # nose - left shoulder - left hip
    [0, 2, 8],  # nose - right shoulder - right hip
    [1, 3, 5],  # left shoulder - left elbow - left wrist
    [2, 4, 6],  # right shoulder - right elbow - right wrist
    [1, 7, 8],  # left shoulder - left hip - right hip
    [2, 8, 7],  # right shoulder - right hip - left hip
    [1, 7, 9],  # left shoulder - left hip - left knee
    [2, 8, 10],  # right shoulder - right hip - right knee
    [3, 1, 7],  # left elbow - left shoulder - left hip
    [4, 2, 8],  # right elbow - right shoulder - right hip
    [7, 9, 11],  # left hip - left knee - left ankle
    [8, 10, 12],  # right hip - right knee - right ankle
    [9, 7, 8],  # left knee - left hip - right hip
    [10, 8, 7],  # right knee - right hip - left hip
]


def pt_in_bbox(pt, xyxy):
    return (
        pt[0] >= xyxy[0] and pt[0] <= xyxy[2] and pt[1] >= xyxy[1] and pt[1] <= xyxy[3]
    )


def merge_coords(all_coords, guide_to_merge, has_confidence=False, is_3d=False):
    new_coords = []
    for to_merge in guide_to_merge:
        x_avg = sum(all_coords[i][0] for i in to_merge) / len(to_merge)
        y_avg = sum(all_coords[i][1] for i in to_merge) / len(to_merge)
        conf = 1.0
        # 3D pose keypoints don't have confidence values (for now)
        if is_3d:
            z_avg = sum(all_coords[i][2] for i in to_merge) / len(to_merge)
            new_coords.append([x_avg, y_avg, z_avg])
        else:
            if has_confidence:
                conf = sum(all_coords[i][2] for i in to_merge) / len(to_merge)
            new_coords.append([x_avg, y_avg, conf])

    return np.array(new_coords)


def get_poem_embedding(pose_coords):
    # Write the coords to a CSV on the server

    if not os.path.isdir("poem_files/camera_pose"):
        os.makedirs("poem_files/camera_pose")

    # Input file to Pr_VIPE code
    with open(
        "poem_files/camera_pose/input.csv", "w", newline="", encoding="utf-8"
    ) as poem_file:
        poemwriter = csv.writer(poem_file)
        poemwriter.writerow(CSV_HEADERS)

        posenorm = np.array(pose_coords)

        # Fake these values - it shouldn't make a difference (hopefully)
        video_width = 1024
        video_height = 768

        posenorm = np.round(posenorm / 100, 2)
        pose_data = (
            np.array(
                [[posenorm[x], posenorm[x + 1], 1] for x in range(0, len(posenorm), 2)]
            )
            .flatten()
            .tolist()
        )
        rowdata = [video_width] + [video_height] + pose_data

        poemwriter.writerow(rowdata)

    # Run the POEM embedding generator on the CSV, producing a new CSV
    subprocess.run(
        [
            "/usr/local/bin/python3",
            "-m",
            "poem.pr_vipe.infer",
            "--input_csv=/app/poem_files/camera_pose/input.csv",
            "--output_dir=/app/poem_files/camera_pose/",
            "--checkpoint_path=/app/lib/poem/checkpoints/checkpoint_Pr-VIPE_2M/model.ckpt-02013963",
        ],
        cwd="/app/lib",
    )

    # Read the new CSV with the embedding and return the contents

    with open(
        "poem_files/camera_pose/unnormalized_embeddings.csv",
        "r",
        newline="",
        encoding="utf-8",
    ) as poem_file:
        poem_line = poem_file.readline().strip().split(",")
        poem_embed = [float(c) for c in poem_line]

        return poem_embed


# Borrowed from https://stackoverflow.com/questions/19729831/angle-between-3-points-in-3d-space
def calculate_angle_in_3d(a, b, c):
    v1 = np.array([a[0] - b[0], a[1] - b[1], a[2] - b[2]])
    v2 = np.array([c[0] - b[0], c[1] - b[1], c[2] - b[2]])

    v1mag = np.sqrt([v1[0] * v1[0] + v1[1] * v1[1] + v1[2] * v1[2]])
    v1norm = np.array([v1[0] / v1mag, v1[1] / v1mag, v1[2] / v1mag])

    v2mag = np.sqrt(v2[0] * v2[0] + v2[1] * v2[1] + v2[2] * v2[2])
    v2norm = np.array([v2[0] / v2mag, v2[1] / v2mag, v2[2] / v2mag])
    res = v1norm[0] * v2norm[0] + v1norm[1] * v2norm[1] + v1norm[2] * v2norm[2]
    angle_rad = np.arccos(res)

    # return math.degrees(angle_rad)
    return angle_rad


def unflatten_pose_data(prediction, key="keypoints"):
    """
    Convert an Open PifPaf pose prediction (a 1D 51-element list) into a 17-element
    list (not a NumPy array) of [x_coord, y_coord, confidence] triples.
    """
    return np.array_split(prediction[key], len(prediction[key]) / 3)


def extract_trustworthy_coords(prediction, key="keypoints"):
    """
    Convert an Open PifPaf pose prediction from a 1D vector of coordinates and confidence
    values to a 17x2 NumPy array containing only the armature coordinates, with
    coordinate values set to NaN,NaN for any coordinate with a confidence value of 0.
    Returns the 17x2 array and a separate list of the original confidence values.
    """
    unflattened_pose = unflatten_pose_data(prediction, key)
    trustworthy_coords = np.array(
        [
            [coords[0], coords[1]] if coords[2] != 0 else [np.NaN, np.NaN]
            for coords in unflattened_pose
        ]
    ).flatten()
    # confidences = [coords[3] for coords in unflattened_pose]
    return trustworthy_coords


def get_pose_extent(prediction, key="keypoints"):
    """Get the min and max x and y coordinates of an Open PifPaf pose prediction"""
    pose_coords = unflatten_pose_data(prediction, key)
    min_x = np.NaN
    min_y = np.NaN
    max_x = np.NaN
    max_y = np.NaN
    for coords in pose_coords:
        # Coordinates with confidence values of 0 are not considered
        if coords[2] == 0:
            continue
        min_x = np.nanmin([min_x, coords[0]])
        min_y = np.nanmin([min_y, coords[1]])
        max_x = np.nanmax([max_x, coords[0]])
        max_y = np.nanmax([max_y, coords[1]])

    return [min_x, min_y, max_x, max_y]


def shift_pose_to_origin(prediction, key):
    """
    Shift the keypoint coordinates of an Open PifPaf pose prediction so that the
    min x and y coordinates of its extent are at the 0,0 origin.
    NOTE: This only returns the modified 'keypoints' portion of the prediction.
    """
    pose_coords = unflatten_pose_data(prediction, key)
    min_x, min_y, _, _ = get_pose_extent(prediction, key)

    for i, coords in enumerate(pose_coords):
        # Coordinates with confidence values of 0 are not modified; these should not
        # be used in any pose representations or calculations, and often (but not
        # always) already have 0,0 coordinates.
        if coords[2] == 0:
            continue
        pose_coords[i] = [coords[0] - min_x, coords[1] - min_y, coords[2]]

    return {"keypoints": np.concatenate(pose_coords, axis=None)}


def rescale_pose_coords(prediction, key="keypoints"):
    """
    Rescale the coordinates of an OpenPifPaf pose prediction so that the extent
    of the pose's long axis is equal to the global POSE_MAX_DIM setting. The
    coordinates of the short axis are scaled by the same factor, and then are
    shifted so that the short axis is centered within the POSE_MAX_DIM extent.
    NOTE: This only returns the modified 'keypoints' portion of the prediction.
    """
    pose_coords = unflatten_pose_data(prediction, key)
    min_x, min_y, max_x, max_y = get_pose_extent(prediction, key)

    scale_factor = POSE_MAX_DIM / np.max([max_x, max_y])

    x_extent = max_x - min_x
    y_extent = max_y - min_y

    if x_extent >= y_extent:
        x_recenter = 0
        y_recenter = round((POSE_MAX_DIM - (scale_factor * y_extent)) / 2)
    else:
        x_recenter = round((POSE_MAX_DIM - (scale_factor * x_extent)) / 2)
        y_recenter = 0

    for i, coords in enumerate(pose_coords):
        # Coordinates with confidence values of 0 are not modified; these should not
        # be used in any pose representations or calculations, and often (but not
        # always) already have 0,0 coordinates.
        if coords[2] == 0:
            continue
        pose_coords[i] = [
            round(coords[0] * scale_factor + x_recenter),
            round(coords[1] * scale_factor + y_recenter),
            coords[2],
        ]

    return {"keypoints": np.concatenate(pose_coords, axis=None)}


def shift_normalize_rescale_pose_coords(prediction, key="keypoints"):
    """
    Convenience function to shift an Open PifPaf pose prediction so that its minimal
    corner is at the origin, then rescale so that it fits into a
    POSE_MAX_DIM * POSE_MAX_DIM extent.
    NOTE: This only returns the modified 'keypoints' portion of the prediction.
    """
    return rescale_pose_coords(shift_pose_to_origin(prediction, key))
