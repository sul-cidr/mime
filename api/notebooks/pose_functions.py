import cv2
from ipycanvas import Canvas, hold_canvas
from IPython.display import display
from ipywidgets import IntProgress
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import os
from pathlib import Path
import pickle
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageEnhance
from scipy.spatial.distance import cosine, correlation
import warnings

import faiss


# All constants are defined up here, though in the future they could be moved into the appropriate sub-modules.

# The body part numberings and armature connectors for the 17-keypoint COCO pose format are defined in
# https://github.com/openpifpaf/openpifpaf/blob/main/src/openpifpaf/plugins/coco/constants.py
# Note that the body part numbers in the connector (skeleton) definitions begin with 1, for some reason, not 0
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

# Default dimensions of the output visualizations ("figure" here simply means a graphic)
FIGURE_WIDTH = 950
FIGURE_HEIGHT = 500

# Default dimension (length, width, maybe depth, eventually) of single pose viz
POSE_MAX_DIM = 100

# XXX ImageDraw does't ship with a scaleable font, so best to use matplotlib's
font_path = os.path.join(
    matplotlib.__path__[0], "mpl-data", "fonts", "ttf", "DejaVuSans.ttf"
)
try:
    LABEL_FONT = ImageFont.truetype(font_path, size=128)
except Exception as e:
    LABEL_FONT = None


# --- POSEDATA MANIPULATION AND COMPARISON FUNCTIONS ---


def unflatten_pose_data(prediction):
    """
    Convert an Open PifPaf pose prediction (a 1D 51-element list) into a 17-element
    list (not a NumPy array) of [x_coord, y_coord, confidence] triples.
    OR, if the input has already been flattened and normalized, in which case it's
    a 1D 34-element list in which the confidence values have been removed and NaNs
    have been provided as x,y pairs for low- or no-confidence coordinates,
    fill in the confidence values with 0 if x or y is NaN and 1 otherwise.
    """
    if len(prediction["keypoints"]) == COORDS_PER_POSE * 3:
        return np.array_split(prediction["keypoints"], len(prediction["keypoints"]) / 3)
    elif len(prediction["keypoints"]) == COORDS_PER_POSE * 2:
        out_array = []
        for coords in np.array_split(prediction["keypoints"], COORDS_PER_POSE):
            if np.isnan(coords[0]) or np.isnan(coords[1]):
                out_array.append([coords[0], coords[1], 0])
            else:
                out_array.append([coords[0], coords[1], 1])
        return out_array


def extract_trustworthy_coords(prediction):
    """
    Convert an Open PifPaf pose prediction from a 1D vector of coordinates and confidence
    values to a 17x2 NumPy array containing only the armature coordinates, with coordinate values
    set to NaN,NaN for any coordinate with a confidence value of 0.
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
    # if "bbox" in prediction:
    #     # bbox format for PifPaf is x0, y0, width, height
    #     bbox = prediction["bbox"]
    #     extent = [bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]]
    #     return extent

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
    Rescale the coordinates of an Open PifPaf pose prediction so that the extent
    of the pose's long axis is equal to the global POSE_MAX_DIM setting. The
    coordinates of the short axis are scaled by the same factor, and then are
    shifted so that the short axis is centered within the POSE_MAX_DIM extent.
    NOTE: This only returns the modified 'keypoints' portion of the prediction.
    """
    pose_coords = unflatten_pose_data(prediction)
    min_x, min_y, max_x, max_y = get_pose_extent(prediction)

    x_extent = max_x - min_x
    y_extent = max_y - min_y

    scale_factor = POSE_MAX_DIM / np.max([x_extent, y_extent])

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
    Convenience function to shift an Open PifPaf pose prediction so that its minimal corner
    is at the origin, then rescale so that it fits into a POSE_MAX_DIM * POSE_MAX_DIM extent.
    NOTE: This only returns the modified 'keypoints' portion of the prediction.
    """
    return rescale_pose_coords(shift_pose_to_origin(prediction))


def compare_poses_cosine_flattened(p1, p2):
    """
    The actual comparison is in this helper function because often the pose data has already
    been flattened by the time the comparison is run.
    """
    return 1 - cosine(p1, p2)


def compare_poses_cosine(p1, p2):
    """
    Calculate the similarity of the 'keypoint' portions of two Open PifPaf pose predictions
    by computing their cosine distance and subtracting this from 1 (so 1=identical).
    """
    return compare_poses_cosine_flattened(
        np.array(unflatten_pose_data(p1))[:, :2].flatten(),
        np.array(unflatten_pose_data(p2))[:, :2].flatten(),
    )


def compare_poses_correlation_flattened(p1, p2):
    """
    The actual comparison is in this helper function because often the pose data has already
    been flattened by the time the comparison is run.
    """
    return 1 - correlation(p1, p2)


def compare_poses_correlation(p1, p2):
    """
    Calculate the similarity of the 'keypoint' portions of two Open PifPaf pose predictions
    by computing their Euclidean distance and subtracting this from 1 (so 1=identical).
    Note that this is only likely to generate reliable results if run on coordinates that
    have been normalized on at least one axis.
    """
    return compare_poses_correlation_flattened(
        np.array(unflatten_pose_data(p1))[:, :2].flatten(),
        np.array(unflatten_pose_data(p2))[:, :2].flatten(),
    )


def compute_joint_angles(prediction):
    """
    Build an additional/alternative feature set for an Open PifPaf pose prediction, composed
    of the angles, measured in radians, of several joints/articulation points on the body (see
    list in code comments below).
    Also compute a rotation value for each angle -- how far it would need to be rotated until
    one armature segment is at a right angle to the vertical (?) plane of the image.
    """
    pose_coords = unflatten_pose_data(prediction)

    joint_angles = []

    # Joints to use:
    joint_angle_points = [
        [3, 5, 6],  # Left ear - left shoulder - right shoulder
        [4, 6, 5],  # Right ear - right shoulder - left shoulder
        [3, 5, 11],  # Left ear - left shoulder - left hip
        [4, 6, 12],  # Right ear - right shoulder - right hip
        [11, 5, 7],  # Left hip - left shoulder - left elbow
        [12, 6, 8],  # Right hip - right shoulder - right elbow
        [5, 7, 9],  # Left shoulder - left elbow - left wrist
        [6, 8, 10],  # Right shoulder - right elbow - right wrist
        [5, 11, 13],  # Left shoulder - left hip - left knee
        [6, 12, 14],  # Right shoulder - right hip - right knee
        [13, 11, 12],  # Left knee - left hip - right hip
        [14, 12, 11],  # Right knee - right hip - left hip
        [11, 13, 15],  # Left hip - left knee - left ankle
        [12, 14, 16],  # Right hip - right knee - right ankle
    ]

    for angle_points in joint_angle_points:
        # Need 3 points to make an angle; if 1 or more are missing, it's a NaN
        if (
            pose_coords[angle_points[0]][2] == 0
            or pose_coords[angle_points[1]][2] == 0
            or pose_coords[angle_points[2]][2] == 0
        ):
            joint_angles.extend([np.NaN, np.NaN])
        else:
            ba = np.array(
                [pose_coords[angle_points[0]][0], pose_coords[angle_points[0]][1]]
            ) - np.array(
                [pose_coords[angle_points[1]][0], pose_coords[angle_points[1]][1]]
            )
            bc = np.array(
                [pose_coords[angle_points[2]][0], pose_coords[angle_points[2]][1]]
            ) - np.array(
                [pose_coords[angle_points[1]][0], pose_coords[angle_points[1]][1]]
            )

            cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
            joint_angles.append(np.arccos(cosine_angle))  # This is the angle

            # The rotation is just the angle between the first segment and a segment
            # drawn straight upwards from the midpoint of the angle.
            bd = np.array(
                [pose_coords[angle_points[1]][0], pose_coords[angle_points[1]][1] - 1]
            ) - np.array(
                [pose_coords[angle_points[1]][0], pose_coords[angle_points[1]][1]]
            )

            rotation = np.arctan2(
                ba[0] * bd[1] - ba[1] * bd[0], ba[0] * bd[0] + ba[1] * bd[1]
            )
            joint_angles.append(rotation)

    return joint_angles


def compare_poses_angles(joint_angles1, joint_angles2):
    """
    Compute a similarity score for two pose predictions that are represented
    as vectors of joint angles. The similarity metric is essentially standard cosine
    similarity (the values in the vectors being angle measurements does not make a
    difference to how it works; they're just treated as numbers), modified to handle
    missing/NaN vector values gracefully. (1=identical)
    """
    angles_dot = np.nansum(np.array(joint_angles1) * np.array(joint_angles2))
    angles_norm = np.sqrt(np.nansum(np.square(np.array(joint_angles1)))) * np.sqrt(
        np.nansum(np.square(np.array(joint_angles2)))
    )
    return angles_dot / angles_norm


def normalize_poses(pose_file, pose_data):
    """
    If previously computed normalized pose data and metadata is not available in
    files, normalize all of the poses in the input pose_data and compute
    accompanying metadata, a flattened list of all poses in the video (for use
    with the vector-search indexer), and mappings from frame and pose IDs to
    positions in the flattened sequence, save them to files and return them.
    """

    data_dir = Path(pose_file.replace(".openpifpaf.json", "")).with_suffix("")

    normalized_pose_file = Path(
        data_dir, Path(pose_file.replace(".openpifpaf.json", ".normalized.p")).name
    )
    metadata_file = Path(
        data_dir, Path(pose_file.replace(".openpifpaf.json", ".metadata.p")).name
    )

    if (os.path.isfile(normalized_pose_file)) and (os.path.isfile(metadata_file)):
        normalized_poses = pickle.load(open(normalized_pose_file, "rb"))
        [normalized_pose_metadata, framepose_to_seqno] = pickle.load(
            open(metadata_file, "rb")
        )
    else:
        print("Computing normalized poses for comparison and clustering")
        print("This may take a while...")
        progress_bar = IntProgress(min=0, max=len(pose_data))
        display(progress_bar)

        # For cluster analysis, each pose must be a 1D array, and all poses must be in a 1D list
        # that includes only the pose keypoint coordinates (not the confidence scores).
        # So we also create a parallel data structure to keep track of the frame number and
        # numbering within the frame of each of the poses.
        normalized_poses = []
        normalized_pose_metadata = []

        framepose_to_seqno = {}
        pose_seqno = 0

        for i, frame in enumerate(pose_data):
            if i % 100 == 0:
                progress_bar.value = i

            for j, pose in enumerate(frame["predictions"]):
                normalized_coords = extract_trustworthy_coords(
                    shift_normalize_rescale_pose_coords(pose)
                )
                normalized_poses.append(normalized_coords)
                normalized_pose_metadata.append({"frameno": i, "poseno": j})

                if i in framepose_to_seqno:
                    framepose_to_seqno[i][j] = pose_seqno
                else:
                    framepose_to_seqno[i] = {j: pose_seqno}

                pose_seqno += 1

        progress_bar.bar_style = "success"

        pickle.dump(normalized_poses, open(normalized_pose_file, "wb"))
        pickle.dump(
            [normalized_pose_metadata, framepose_to_seqno], open(metadata_file, "wb")
        )

    # Need to rebuild an actual structure of normalized pose data that parallels the
    # structure of pose_data (normalized_poses doesn't actually do this).
    normalized_pose_data = []

    for frameno, frame in enumerate(pose_data):
        frame_predictions = {"predictions": []}

        if frameno in framepose_to_seqno:
            for poseno in framepose_to_seqno[frameno]:
                frame_predictions["predictions"].append(
                    normalized_poses[framepose_to_seqno[frameno][poseno]]
                )
        normalized_pose_data.append(frame_predictions)

    return [
        normalized_poses,
        normalized_pose_metadata,
        framepose_to_seqno,
        normalized_pose_data,
    ]


def get_all_pose_angles(pose_file, pose_data, framepose_to_seqno):
    """
    If previously computed pose angle data is not available,
    run pose_angles to get angle data (in radians) for various
    armature joints on each pose in pose_data; create a parallel
    data structure to pose_data that includes this angle data as
    well as a flattened list of all per-pose angles in the video,
    for use with the vector-search indexer.
    """

    data_dir = Path(pose_file.replace(".openpifpaf.json", "")).with_suffix("")

    angles_data_file = Path(
        data_dir, Path(pose_file.replace(".openpifpaf.json", ".angles.p")).name
    )

    if os.path.isfile(angles_data_file):
        [pose_angle_data, pose_angles] = pickle.load(open(angles_data_file, "rb"))
    else:
        pose_angles = []
        # pose_angles_metadata = [] # This is redundant with normalized_pose_metadata...
        # framepose_to_seqno = {} # Already computed when finding normalized poses
        pose_seqno = 0

        print("Precomputing pose angle data")

        progress_bar = IntProgress(min=0, max=len(pose_data))
        display(progress_bar)

        for i, frame in enumerate(pose_data):
            if i % 100 == 0:
                progress_bar.value = i

            for pose in frame["predictions"]:
                angles = compute_joint_angles(pose)

                pose_angles.append(angles)

                pose_seqno += 1

        progress_bar.bar_style = "success"

        # Need to rebuild an actual structure of pose angle data that parallels the
        # structure of pose_data.
        pose_angle_data = []

        for frameno, frame in enumerate(pose_data):
            frame_predictions = {"predictions": []}

            if frameno in framepose_to_seqno:
                for poseno in framepose_to_seqno[frameno]:
                    frame_predictions["predictions"].append(
                        pose_angles[framepose_to_seqno[frameno][poseno]]
                    )
            pose_angle_data.append(frame_predictions)

        pickle.dump([pose_angle_data, pose_angles], open(angles_data_file, "wb"))

    return [pose_angle_data, pose_angles]


# --- POSE DRAWING AND VISUALIZATION FUNCTIONS ---


def image_from_video_frame(video_file, frameno):
    """Grab the specified frame from the video and converts it into an RGBA array"""
    cap = cv2.VideoCapture(video_file)
    cap.set(1, frameno)
    ret, img = cap.read()
    rgb_bg = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.cvtColor(rgb_bg, cv2.COLOR_RGB2RGBA)
    image = np.asarray(img)
    cap.release()
    return image


def extract_pose_background(pose_pred, video_file, pose_frameno):
    """
    Extract the source image region covered by a detected pose's bounding box
    after the bounding box has been expanded to a sqare with side length
    equal to the long axis of the original bounding box (so the short axis
    of the original bounding box is centered in the expanded box), then adding
    letterbox/pillarbox bands wherever the expanded bounding box happens to
    go beyond the edges of the source image.
    """
    min_x, min_y, max_x, max_y = get_pose_extent(pose_pred)

    x_extent = max_x - min_x
    y_extent = max_y - min_y

    if x_extent >= y_extent:
        x_padding = 0
        y_padding = (x_extent - y_extent) / 2
    else:
        x_padding = (y_extent - x_extent) / 2
        y_padding = 0

    pose_frame_image = image_from_video_frame(video_file, pose_frameno)

    # Add transparent letterboxing/pillarboxing pixels if a square cutout around
    # the pose (needed for normalization) exceeds the frame of the image
    x_start = round(min_x - x_padding)
    x_stop = round(max_x + x_padding)
    y_start = round(min_y - y_padding)
    y_stop = round(max_y + y_padding)

    x_start_pad = 0
    x_stop_pad = 0
    y_start_pad = 0
    y_stop_pad = 0

    if x_start < 0:
        x_start_pad = -x_start
        x_start = 0
    if x_stop >= pose_frame_image.shape[1]:
        x_stop_pad = x_stop - pose_frame_image.shape[1]
        x_stop = pose_frame_image.shape[1] - 1
    if y_start < 0:
        y = y_start_pad = -y_start
        y_start = 0
    if y_stop >= pose_frame_image.shape[0]:
        y_stop_pad = y_stop - pose_frame_image.shape[0]
        y_stop = pose_frame_image.shape[0] - 1

    pose_base_image = pose_frame_image[y_start:y_stop, x_start:x_stop]
    if x_start_pad > 0:
        pad_array = np.zeros((pose_base_image.shape[0], x_start_pad, 4), np.uint8)
        pose_base_image = np.concatenate((pad_array, pose_base_image), axis=1)
    if x_stop_pad > 0:
        pad_array = np.zeros((pose_base_image.shape[0], x_stop_pad, 4), np.uint8)
        pose_base_image = np.concatenate((pose_base_image, pad_array), axis=1)
    if y_start_pad > 0:
        pad_array = np.zeros((y_start_pad, pose_base_image.shape[1], 4), np.uint8)
        pose_base_image = np.concatenate((pad_array, pose_base_image), axis=0)
    if y_stop_pad > 0:
        pad_array = np.zeros((y_stop_pad, pose_base_image.shape[1], 4), np.uint8)
        pose_base_image = np.concatenate((pose_base_image, pad_array), axis=0)

    return pose_base_image


def draw_armatures(pose_coords, drawing, line_prevalences=[], x_shift=0, y_shift=0):
    """
    Draw, colorize and adjust the transparency of armature connections in the pose_coords
    data from an Open PifPaf pose prediction. This function can receive pose coordinates
    as 3-tuples (x, y, confidence) or 2-tuples (x, y). In the latter case, coordinates
    with 0 confidence are (NaN, Nan), and nonzero confidence/armature prevalence values
    can be provided via the line_prevalences parameter. For both types, 0-confidence armature
    lines are not drawn. The other armature lines are drawn increasingly transparent as
    their confidence scores/prevalences approach 0.
    Note that this function can be run on its own to draw a simple pose armature skeleton
    or via add_pose_to_drawing() to add bounding box visualizations and pose number IDs to
    the drawing. As with add_pose_to_drawing(), a background can already have been added
    to the drawing, or it can be added/superimposed later (or left blank).
    """
    for i, seg in enumerate(OPP_COCO_SKELETON):
        line_color = ImageColor.getrgb(OPP_COCO_COLORS[i])

        # If line_prevalences are provided, we know the pose coords don't contain confidence
        # values, and instead the x and y values are NaN if the point has 0 confidence
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


def add_pose_to_drawing(pose_prediction, drawing, seqno=None, show_bbox=False):
    """
    Draw the colorized and confidence-brightened connecting armatures of a pose
    prediction skeleton from Open PifPaf on a background (which can be blank or) adding a
    bounding box and pose sequence ID number to the drawing if provided. A background
    can already have been added to the drawing, or it can be added/superimposed later
    (or left blank).
    """
    pose_coords = unflatten_pose_data(pose_prediction)

    drawing = draw_armatures(pose_coords, drawing)

    if "bbox" in pose_prediction:
        bbox = pose_prediction["bbox"]
    else:
        extent = get_pose_extent(pose_prediction)
        bbox = [extent[0], extent[1], extent[2] - extent[0], extent[3] - extent[1]]

    # bbox format for PifPaf is x0, y0, width, height
    # Also note that both PifPaf and PIL/ImageDraw place (0,0) at top left, not bottom left
    upper_left = (int(bbox[0] * UPSCALE), int(bbox[1] * UPSCALE))
    lower_right = (
        int((bbox[0] + bbox[2]) * UPSCALE),
        int((bbox[1] + bbox[3]) * UPSCALE),
    )

    pose_outline_color = "blue"
    if seqno is not None:
        pose_label = str(seqno + 1)

    if "tracking_id" in pose_prediction:
        pose_outline_color = "purple"
        pose_label = str(pose_prediction["tracking_id"])

    if show_bbox:
        shape = [upper_left, lower_right]
        drawing.rectangle(shape, outline=pose_outline_color, width=1 * UPSCALE)

    if seqno is not None:
        drawing.text(
            upper_left,
            pose_label,
            font=LABEL_FONT,
            align="right",
            fill=pose_outline_color,
        )

    return drawing


def normalize_and_draw_pose(pose_prediction, video_file, frameno=None):
    """
    Shift an Open PifPaf pose prediction to border the 0,0 origin and then scale it to
    POSE_MAX_DIM*POSE_MAX_DIM pixels and draw the pose into the normalized space, using
    upscaling/downscaling to avoid pixelated lines. If a source frameno is provided,
    this also extracts the source image region of the pose and draws it behind the plotted
    pose. Note also that add_pose_to_drawing() will draw armature lines with lower
    confidence values as more transparent than high-confidence lines.
    """
    original_prediction = pose_prediction
    pose_prediction = shift_normalize_rescale_pose_coords(pose_prediction)
    # Can also grab the background image and excerpt/scale it to match, if desired
    if frameno is not None:
        # Get the frame image
        bg_img = image_from_video_frame(video_file, frameno)
        pose_base_image = extract_pose_background(
            original_prediction, video_file, frameno
        )
        resized_image = cv2.resize(
            pose_base_image,
            dsize=(POSE_MAX_DIM * UPSCALE, POSE_MAX_DIM * UPSCALE),
            interpolation=cv2.INTER_LANCZOS4,
        )
        bg_img = Image.fromarray(resized_image)
    else:
        bg_img = Image.new("RGBA", (POSE_MAX_DIM * UPSCALE, POSE_MAX_DIM * UPSCALE))
    drawing = ImageDraw.Draw(bg_img)
    drawing = add_pose_to_drawing(pose_prediction, drawing)
    bg_img = bg_img.resize(
        (POSE_MAX_DIM, POSE_MAX_DIM), resample=Image.Resampling.LANCZOS
    )
    return bg_img


def draw_normalized_and_unflattened_pose(pose_prediction, armature_prevalences=[]):
    """
    Variant of normalize_and_draw_pose() for a pose that has already been normalized and
    may have armature prevalence values calculated separately. Currently this is only used
    to draw averaged poses as representatives of pose clusters.
    """
    bg_img = Image.new("RGBA", (POSE_MAX_DIM * UPSCALE, POSE_MAX_DIM * UPSCALE))
    drawing = ImageDraw.Draw(bg_img)
    drawing = draw_armatures(pose_prediction, drawing, armature_prevalences)
    return bg_img


def draw_frame(frame, video_width, video_height, bg_img=None):
    """
    Draw all detected poses in the specified frame, superimposing them on the frame image,
    if provided.
    """
    # The only way to get smooth(er) lines in the pose armatures via PIL ImageDraw is to
    # upscale the entire image by some factor, draw the lines, then downscale back to the
    # original resolution while applying Lanczos resampling, because ImageDraw doesn't do
    # any native anti-aliasing.
    if bg_img is None:
        bg_img = Image.new("RGBA", (video_width * UPSCALE, video_height * UPSCALE))
    else:
        bg_img = bg_img.resize((video_width * UPSCALE, video_height * UPSCALE))

    drawing = ImageDraw.Draw(bg_img)

    for i, pose_prediction in enumerate(frame["predictions"]):
        drawing = add_pose_to_drawing(pose_prediction, drawing, i, show_bbox=True)

    bg_img = bg_img.resize(
        (video_width, video_height), resample=Image.Resampling.LANCZOS
    )

    return bg_img


def draw_normalized_pose_on_canvas(pose_prediction, canvas):
    """
    Draw the specified pose prediction on an ipycanvas. Normalized poses
    do not have confidence values for each coordinate pair; rather if the
    pair consists of NaNs, that armature point should be skipped.
    """
    pose_coords = np.array_split(pose_prediction, len(pose_prediction) / 2)

    for i, seg in enumerate(OPP_COCO_SKELETON):
        if (
            np.isnan(pose_coords[seg[0] - 1][0])
            or np.isnan(pose_coords[seg[0] - 1][1])
            or np.isnan(pose_coords[seg[1] - 1][0])
            or np.isnan(pose_coords[seg[1] - 1][1])
        ):
            continue

        canvas.stroke_style = OPP_COCO_COLORS[i]
        canvas.line_width = 2

        canvas.stroke_line(
            pose_coords[seg[0] - 1][0],
            pose_coords[seg[0] - 1][1],
            pose_coords[seg[1] - 1][0],
            pose_coords[seg[1] - 1][1],
        )


def draw_pose_on_canvas(pose_prediction, canvas, x_shift=0, y_shift=0):
    """
    Draw the specified pose prediction on an ipycanvas. If the confidence
    value for a given coordinate pair is 0, skip that armature point.
    """
    pose_coords = np.array_split(
        pose_prediction["keypoints"], len(pose_prediction["keypoints"]) / 3
    )

    for i, seg in enumerate(OPP_COCO_SKELETON):
        if pose_coords[seg[0] - 1][2] == 0 or pose_coords[seg[1] - 1][2] == 0:
            continue

        canvas.stroke_style = OPP_COCO_COLORS[i]
        canvas.line_width = 2

        canvas.stroke_line(
            pose_coords[seg[0] - 1][0] - x_shift,
            pose_coords[seg[0] - 1][1] - y_shift,
            pose_coords[seg[1] - 1][0] - x_shift,
            pose_coords[seg[1] - 1][1] - y_shift,
        )


def draw_frame_on_canvas(frame, canvas):
    """Draw all the poses in the specified frame on an ipycanvas"""
    for pose_prediction in frame["predictions"]:
        draw_pose_on_canvas(pose_prediction, canvas)


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


# --- POSE TRACKING VISUALIZATION FUNCTIONS ---


def snapshot_pose_track(tracking_id, pose_tracks, normalized_pose_data):
    """
    Superimpose all of the instances of a pose across a tracking sequence, allowing
    for lateral movement -- so the size of the background is the combined extent of
    all of the poses within the original frame.
    """

    # Could just plot these on the same plot via pyplot, but this looks a bit better
    images_array = []

    for track_frame in pose_tracks[tracking_id]:
        pose_pil_img = draw_normalized_and_unflattened_pose(
            unflatten_pose_data(
                normalized_pose_data[track_frame["frameno"]]["predictions"][
                    track_frame["poseno"]
                ]
            )
        )
        images_array.append(np.array(pose_pil_img))

    images_array = np.array(images_array, dtype=float)

    avg_pose_img = np.mean(images_array, axis=0).astype(np.uint8)

    avg_pil_img = Image.fromarray(avg_pose_img)
    enhancer = ImageEnhance.Contrast(avg_pil_img)
    enhanced_pil_img = enhancer.enhance(2.0)

    plt.imshow(enhanced_pil_img)


def animate_pose_track(tracking_id, pose_tracks, normalized_pose_data, video_fps):
    """
    Iteratively draw all of the instances of a pose across a tracking sequence
    at the time points when they appear, blanking the background between frames.
    """

    canvas = Canvas(width=POSE_MAX_DIM, height=POSE_MAX_DIM, sync_image_data=True)

    display(canvas)

    with hold_canvas():
        for t, track_frame in enumerate(pose_tracks[tracking_id]):
            canvas.clear()
            draw_normalized_pose_on_canvas(
                normalized_pose_data[track_frame["frameno"]]["predictions"][
                    track_frame["poseno"]
                ],
                canvas,
            )
            if t + 1 < len(pose_tracks[tracking_id]):
                sleep_len = (
                    (
                        pose_tracks[tracking_id][t + 1]["frameno"]
                        - pose_tracks[tracking_id][t]["frameno"]
                    )
                    * 1000
                    / video_fps
                )
                canvas.sleep(sleep_len)


def get_track_boundaries(tracking_id, pose_tracks, pose_data):
    """
    Determine the maximum extent of all pose instances in a tracking sequence,
    relative to the original frame.
    """

    track_boundaries = []
    for track_frame in pose_tracks[tracking_id]:
        track_boundaries.append(
            get_pose_extent(
                pose_data[track_frame["frameno"]]["predictions"][track_frame["poseno"]]
            )
        )

    return [
        np.min(np.array(track_boundaries)[:, 0]),
        np.min(np.array(track_boundaries)[:, 1]),
        np.max(np.array(track_boundaries)[:, 2]),
        np.max(np.array(track_boundaries)[:, 3]),
    ]


def snapshot_pose_track_noclipping(tracking_id, pose_tracks, pose_data):
    """
    Plot all of the instances of a pose across a tracking sequence in their original
    positions in the video frame, so the dimensions of the background are the combined
    extent of all of the poses, allowing for lateral movement.
    """

    min_x, min_y, max_x, max_y = get_track_boundaries(
        tracking_id, pose_tracks, pose_data
    )

    bg_img = Image.new(
        "RGBA", (round(max_x - min_x) * UPSCALE, round(max_y - min_y) * UPSCALE)
    )
    drawing = ImageDraw.Draw(bg_img)

    for track_frame in pose_tracks[tracking_id]:
        pose_keypoints = pose_data[track_frame["frameno"]]["predictions"][
            track_frame["poseno"]
        ]["keypoints"]
        pose_coords = np.array_split(pose_keypoints, len(pose_keypoints) / 3)
        drawing = draw_armatures(pose_coords, drawing, x_shift=min_x, y_shift=min_y)

    bg_img = bg_img.resize(
        (round(max_x - min_x), round(max_y - min_y)), resample=Image.Resampling.LANCZOS
    )

    plt.imshow(bg_img)


def animate_pose_track_noclipping_bg(
    tracking_id, pose_tracks, pose_data, video_file, video_fps
):
    """
    Iteratively draw all of the instances of a pose across a tracking sequence at the
    time points when they appear, as well as all of the source video frame excerpts
    that appear behind the lateral extent of the tracking sequence. When no pose was
    detected in a particular frame, the background should still be updated, maintaining
    the original frame rate of the video.
    """

    def draw_frame_bg_on_canvas(canvas, frameno):
        pose_frame_image = image_from_video_frame(video_file, frameno)
        pose_base_image = pose_frame_image[
            round(min_y) : round(max_y), round(min_x) : round(max_x)
        ]
        canvas.put_image_data(pose_base_image, 0, 0)

    min_x, min_y, max_x, max_y = get_track_boundaries(
        tracking_id, pose_tracks, pose_data
    )
    sleep_len = 1000 / video_fps

    canvas = Canvas(
        width=round(max_x - min_x), height=round(max_y - min_y), sync_image_data=True
    )
    display(canvas)

    with hold_canvas():
        draw_track_index = 0
        for frameno in range(
            pose_tracks[tracking_id][0]["frameno"],
            pose_tracks[tracking_id][-1]["frameno"] + 1,
        ):
            canvas.clear()
            draw_frame_bg_on_canvas(canvas, frameno)

            if pose_tracks[tracking_id][draw_track_index]["frameno"] == frameno:
                poseno = pose_tracks[tracking_id][draw_track_index]["poseno"]
                draw_pose_on_canvas(
                    pose_data[frameno]["predictions"][poseno],
                    canvas,
                    x_shift=min_x,
                    y_shift=min_y,
                )
                draw_track_index += 1

            canvas.sleep(sleep_len)


def animate_pose_track_noclipping(tracking_id, pose_tracks, pose_data, video_fps):
    """
    Iteratively draw all of the instances of a pose across a tracking sequence at the
    time points when they appear. Freeze the pose in place for the duration of the frames
    during which no pose from the tracklet was detected, maintaining the original frame
    rate of the video.
    """
    min_x, min_y, max_x, max_y = get_track_boundaries(
        tracking_id, pose_tracks, pose_data
    )

    canvas = Canvas(
        width=round(max_x - min_x), height=round(max_y - min_y), sync_image_data=True
    )

    display(canvas)

    with hold_canvas():
        for t, track_frame in enumerate(pose_tracks[tracking_id]):
            canvas.clear()

            draw_pose_on_canvas(
                pose_data[track_frame["frameno"]]["predictions"][track_frame["poseno"]],
                canvas,
                x_shift=min_x,
                y_shift=min_y,
            )
            if t + 1 < len(pose_tracks[tracking_id]):
                this_pose_frameno = pose_tracks[tracking_id][t]["frameno"]
                next_pose_frameno = pose_tracks[tracking_id][t + 1]["frameno"]

                sleep_len = (next_pose_frameno - this_pose_frameno) * 1000 / video_fps
                canvas.sleep(sleep_len)


def draw_all_tracklets(pose_tracks, pose_data, video_fps):
    """
    This  generates tracklet "snapshots" starting from the beginning of the video
    (it needs to be stopped manually or it will run all the way to the end of the video)
    """

    for tracking_id in pose_tracks:
        track_duration = (
            pose_tracks[tracking_id][-1]["frameno"]
            - pose_tracks[tracking_id][0]["frameno"]
        ) / video_fps
        # print("Track duration in seconds:", track_duration)
        # print("Number of poses:", len(pose_tracks[tracking_id]))

        if track_duration > 1:
            print("Snapshotting track", tracking_id)
            snapshot_pose_track_noclipping(tracking_id, pose_tracks, pose_data)
            plt.show()
        else:
            print("Track", tracking_id, "is <1s, skipping")


# --- POSE CLUSTERING FUNCTIONS ---


NUMBER_OF_CLUSTERS = 100
CLUSTERS_TO_DRAW = 10
IMAGE_SAMPLE = 100  # Only contribute 1 in 100 images to the background average
AVERAGE_BACKGROUNDS = True  # Set to True to average the pose backgrounds


def cluster_all_poses(faiss_input):
    """
    Cluster video poses into NUMBER_OF_CLUSTERS via K-means, using the similarity
    indexing already computed via FAISS.
    """
    print(f"Clustering video poses into {NUMBER_OF_CLUSTERS} clusters")
    kmeans_faiss = faiss.Kmeans(d=faiss_input.shape[1], k=NUMBER_OF_CLUSTERS, niter=100)
    kmeans_faiss.train(faiss_input)
    _, cluster_labels = kmeans_faiss.index.search(faiss_input, 1)
    cluster_labels = np.array(cluster_labels).flatten()

    return cluster_labels


def compute_cluster_distribution(cluster_labels, viz=True):
    """
    Compute and visualize a bar plot of the number of poses in each of the
    NUMBER_OF_CLUSTERS similarity clusters, ordered by decreasing size.
    """
    bin_counts = {}
    cluster_to_pose = {}

    for i, clust in enumerate(cluster_labels):
        if clust not in bin_counts:
            bin_counts[clust] = 1
        else:
            bin_counts[clust] += 1
        if clust not in cluster_to_pose:
            cluster_to_pose[clust] = [i]
        else:
            cluster_to_pose[clust].append(i)

    sorted_bin_counts = dict(
        sorted(bin_counts.items(), key=lambda item: item[1], reverse=True)
    )
    sorted_bin_counts_list = list(sorted_bin_counts.values())

    if viz:
        plt.bar(range(len(sorted_bin_counts_list)), sorted_bin_counts_list)
        plt.xlabel("cluster rank (by size)")
        plt.ylabel("# poses")
        plt.show()

    return [cluster_to_pose, sorted_bin_counts]


def draw_cluster_representatives(
    cluster_to_pose,
    sorted_bin_counts,
    normalized_poses,
    normalized_pose_metadata,
    pose_data,
    video_file,
    clusters_to_draw=CLUSTERS_TO_DRAW,
    average_backgrounds=AVERAGE_BACKGROUNDS,
):
    """
    For the first CLUSTERS_TO_DRAW pose clusters by descending population,
    average the normalized coordinates (and confidence values) of all pose
    armature links in the cluster; if average_backgrounds is True, do the
    same for the pixel values of the pose source images, then plot the
    results.
    """

    print("Drawing averages of cluster poses (and backgrounds, if requested)")

    for k in list(sorted_bin_counts.keys())[:clusters_to_draw]:
        cluster_poses = []
        images_array = []

        # Use some matplotlib weirdness to draw the stick figures in higher resolution
        # but with the same axis labels (0-100 "pixels")
        fig, ax = plt.subplots()
        fig.set_size_inches(UPSCALE * 100 / fig.dpi, UPSCALE * 100 / fig.dpi)
        fig.canvas.draw()

        print("Cluster:", k, "| total poses:", len(cluster_to_pose[k]))

        for i, pose_id in enumerate(cluster_to_pose[k]):
            cluster_poses.append(normalized_poses[pose_id])

            # Don't average the background of every pose in the cluster,
            # because that usually takes way too long
            if average_backgrounds and (i % IMAGE_SAMPLE) == 0:
                # Get the original posedata for the pose in order to extract the background image
                pose_frameno = normalized_pose_metadata[pose_id]["frameno"]
                poseno = normalized_pose_metadata[pose_id]["poseno"]
                pose_pred = pose_data[pose_frameno]["predictions"][poseno]

                pose_base_image = extract_pose_background(
                    pose_pred, video_file, pose_frameno
                )

                # Resize/normalize the cutout background dimensions, just as is done
                # for the pose itself
                resized_image = cv2.resize(
                    pose_base_image,
                    dsize=(POSE_MAX_DIM * UPSCALE, POSE_MAX_DIM * UPSCALE),
                    interpolation=cv2.INTER_LANCZOS4,
                )
                images_array.append(resized_image)

        if average_backgrounds:
            images_array = np.array(images_array, dtype=float)

            # Average the RGB values of all of the pose background images
            avg_background_img = np.mean(images_array, axis=0).astype(np.uint8)
            plt.imshow(avg_background_img)

        with warnings.catch_warnings():
            warnings.filterwarnings(action="ignore", message="Mean of empty slice")
            cluster_average = np.nanmean(np.array(cluster_poses), axis=0).tolist()

        armature_prevalences = get_armature_prevalences(cluster_poses)
        cluster_average = np.array_split(cluster_average, len(cluster_average) / 2)
        cluster_average_img = draw_normalized_and_unflattened_pose(
            cluster_average, armature_prevalences=armature_prevalences
        )

        plt.imshow(cluster_average_img)
        axis_labels = [0] + list(range(0, 100, 20))
        axis_label_locs = [lab * UPSCALE for lab in axis_labels]

        ax.xaxis.set_major_locator(mticker.FixedLocator(axis_label_locs))
        ax.set_xticklabels(axis_labels)
        ax.yaxis.set_major_locator(mticker.FixedLocator(axis_label_locs))
        ax.set_yticklabels(axis_labels)
        plt.show()
