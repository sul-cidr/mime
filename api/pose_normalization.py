import numpy as np

# Default dimension (length, width, maybe depth, eventually) of single pose viz
POSE_MAX_DIM = 100


def unflatten_pose_data(prediction):
    """
    Convert an Open PifPaf pose prediction (a 1D 51-element list) into a 17-element
    list (not a NumPy array) of [x_coord, y_coord, confidence] triples.
    """
    return np.array_split(prediction["keypoints"], len(prediction["keypoints"]) / 3)


def extract_trustworthy_coords(prediction):
    """
    Convert an Open PifPaf pose prediction from a 1D vector of coordinates and confidence
    values to a 17x2 NumPy array containing only the armature coordinates, with
    coordinate values set to NaN,NaN for any coordinate with a confidence value of 0.
    Returns the 17x2 array and a separate list of the original confidence values.
    """
    unflattened_pose = unflatten_pose_data(prediction)
    trustworthy_coords = np.array(
        [
            [coords[0], coords[1]] if coords[2] != 0 else [np.NaN, np.NaN]
            for coords in unflattened_pose
        ]
    ).flatten()
    # confidences = [coords[3] for coords in unflattened_pose]
    return trustworthy_coords


def get_pose_extent(prediction):
    """Get the min and max x and y coordinates of an Open PifPaf pose prediction"""
    pose_coords = unflatten_pose_data(prediction)
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


def shift_pose_to_origin(prediction):
    """
    Shift the keypoint coordinates of an Open PifPaf pose prediction so that the
    min x and y coordinates of its extent are at the 0,0 origin.
    NOTE: This only returns the modified 'keypoints' portion of the prediction.
    """
    pose_coords = unflatten_pose_data(prediction)
    min_x, min_y, max_x, max_y = get_pose_extent(prediction)

    for i, coords in enumerate(pose_coords):
        # Coordinates with confidence values of 0 are not modified; these should not
        # be used in any pose representations or calculations, and often (but not
        # always) already have 0,0 coordinates.
        if coords[2] == 0:
            continue
        pose_coords[i] = [coords[0] - min_x, coords[1] - min_y, coords[2]]

    return {"keypoints": np.concatenate(pose_coords, axis=None)}


def rescale_pose_coords(prediction):
    """
    Rescale the coordinates of an OpenPifPaf pose prediction so that the extent
    of the pose's long axis is equal to the global POSE_MAX_DIM setting. The
    coordinates of the short axis are scaled by the same factor, and then are
    shifted so that the short axis is centered within the POSE_MAX_DIM extent.
    NOTE: This only returns the modified 'keypoints' portion of the prediction.
    """
    pose_coords = unflatten_pose_data(prediction)
    min_x, min_y, max_x, max_y = get_pose_extent(prediction)

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


def shift_normalize_rescale_pose_coords(prediction):
    """
    Convenience function to shift an Open PifPaf pose prediction so that its minimal
    corner is at the origin, then rescale so that it fits into a
    POSE_MAX_DIM * POSE_MAX_DIM extent.
    NOTE: This only returns the modified 'keypoints' portion of the prediction.
    """
    return rescale_pose_coords(shift_pose_to_origin(prediction))
