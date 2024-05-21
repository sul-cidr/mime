import numpy as np

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
    [0],
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
