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
    min_x, min_y, max_x, max_y = get_pose_extent(prediction, key)

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
