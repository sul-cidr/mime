import numpy as np
from PIL import Image, ImageColor, ImageDraw

# The body part numberings and armature connectors for the 17-keypoint COCO pose format
# are defined in
# https://github.com/openpifpaf/openpifpaf/blob/main/src/openpifpaf/plugins/coco/constants.py
# Note that the body part numbers in the connector (skeleton) definitions begin with 1,
# for some reason, not 0
OPP_COCO_SKELETON = [
    (16, 14),
    (14, 12),
    (17, 15),
    (15, 13),
    (12, 13),
    (6, 12),
    (7, 13),
    (6, 7),
    (6, 8),
    (7, 9),
    (8, 10),
    (9, 11),
    (2, 3),
    (1, 2),
    (1, 3),
    (2, 4),
    (3, 5),
    (4, 6),
    (5, 7),
]
OPP_COCO_COLORS = [
    "orangered",
    "orange",
    "blue",
    "lightblue",
    "darkgreen",
    "red",
    "lightgreen",
    "pink",
    "plum",
    "purple",
    "brown",
    "saddlebrown",
    "mediumorchid",
    "gray",
    "salmon",
    "chartreuse",
    "lightgray",
    "darkturquoise",
    "goldenrod",
]

UPSCALE = 5  # See draw_frame()

COORDS_PER_POSE = 17

# Default dimension (length, width, maybe depth, eventually) of single pose viz
POSE_MAX_DIM = 100


def draw_armatures(pose_coords, drawing, line_prevalences=None, x_shift=0, y_shift=0):
    """
    Draw, colorize and adjust the transparency of armature connections in the
    pose_coords data from an Open PifPaf pose prediction. This function can receive pose
    coordinates as 3-tuples (x, y, confidence) or 2-tuples (x, y). In the latter case,
    coordinates with 0 confidence are (NaN, Nan), and nonzero confidence/armature
    prevalence values can be provided via the line_prevalences parameter. For both types,
    0-confidence armature lines are not drawn. The other armature lines are drawn
    increasingly transparent as their confidence scores/prevalences approach 0.
    Note that this function can be run on its own to draw a simple pose armature skeleton
    or via add_pose_to_drawing() to add bounding box visualizations and pose number IDs
    to the drawing. As with add_pose_to_drawing(), a background can already have been
    added to the drawing, or it can be added/superimposed later (or left blank).
    """
    if line_prevalences is None:
        line_prevalences = []
    for i, seg in enumerate(OPP_COCO_SKELETON):
        line_color = ImageColor.getrgb(OPP_COCO_COLORS[i])

        # If line_prevalences are provided, we know the pose coords don't contain
        # confidence values, and instead the x and y values are NaN if the point
        # has 0 confidence
        if len(line_prevalences) > 0:
            if np.isnan(pose_coords[seg[0] - 1][0]) or np.isnan(
                pose_coords[seg[1] - 1][1]
            ):
                continue
            line_color = line_color + (round(line_prevalences[i] * 256),)
        else:
            if pose_coords[seg[0] - 1][2] == 0 or pose_coords[seg[1] - 1][2] == 0:
                continue
            segment_confidence = (
                pose_coords[seg[0] - 1][2] + pose_coords[seg[1] - 1][2]
            ) / 2
            line_color = line_color + (round(segment_confidence * 256),)

        shape = [
            (
                round((pose_coords[seg[0] - 1][0] - x_shift) * UPSCALE),
                round((pose_coords[seg[0] - 1][1] - y_shift) * UPSCALE),
            ),
            (
                round((pose_coords[seg[1] - 1][0] - x_shift) * UPSCALE),
                round((pose_coords[seg[1] - 1][1] - y_shift) * UPSCALE),
            ),
        ]
        drawing.line(shape, fill=line_color, width=2 * UPSCALE)

    return drawing


def draw_normalized_and_unflattened_pose(pose_prediction, armature_prevalences=[]):
    """
    Variant of normalize_and_draw_pose() for a pose that has already been normalized and
    may have armature prevalence values calculated separately. Currently this is only used
    to draw averaged poses as representatives of pose clusters.
    """
    bg_img = Image.new(
        "RGBA", (POSE_MAX_DIM * UPSCALE, POSE_MAX_DIM * UPSCALE), (0, 0, 0, 0)
    )
    drawing = ImageDraw.Draw(bg_img)
    drawing = draw_armatures(pose_prediction, drawing, armature_prevalences)
    return bg_img


def get_armature_prevalences(cluster_poses):
    """
    Count how many times each limb/armature element appears in a group of poses,
    which then can be used to fade out the elements that are less well represented
    in the pose when computing an averaged representative pose from the cluster.
    """
    armature_appearances = [0] * len(OPP_COCO_SKELETON)
    for pose_coords in cluster_poses:
        pose_coords = np.array_split(pose_coords, len(pose_coords) / 2)

        for i, seg in enumerate(OPP_COCO_SKELETON):
            if not np.isnan(pose_coords[seg[0] - 1][0]) and not np.isnan(
                pose_coords[seg[1] - 1][1]
            ):
                armature_appearances[i] += 1
    return [segcount / len(cluster_poses) for segcount in armature_appearances]
