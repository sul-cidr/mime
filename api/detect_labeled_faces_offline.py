#!/usr/bin/env python3

"""CLI to run face detection on a video file and write the output to a JSON file."""

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path

import cv2
import numpy as np
from deepface import DeepFace
from deepface.commons import functions
from retinaface import RetinaFace  # this is not a must dependency
from retinaface.commons import postprocess
from rich.logging import RichHandler

frontend_model_name = "ArcFace"  # "DeepFace" (could be a cmd line param)


def detect_retinaface(backend_model, img, align=True):
    resp = []

    obj = RetinaFace.detect_faces(img, model=backend_model, threshold=0.9)

    if isinstance(obj, dict):
        for face_idx in obj.keys():
            identity = obj[face_idx]
            facial_area = identity["facial_area"]

            y = facial_area[1]
            h = facial_area[3] - y
            x = facial_area[0]
            w = facial_area[2] - x
            img_region = [x, y, w, h]
            confidence = identity["score"]

            # detected_face = img[int(y):int(y+h), int(x):int(x+w)] #opencv
            detected_face = img[
                facial_area[1] : facial_area[3], facial_area[0] : facial_area[2]
            ]

            if align:
                landmarks = identity["landmarks"]
                left_eye = landmarks["left_eye"]
                right_eye = landmarks["right_eye"]
                nose = landmarks["nose"]
                # mouth_right = landmarks["mouth_right"]
                # mouth_left = landmarks["mouth_left"]

                detected_face = postprocess.alignment_procedure(
                    detected_face, right_eye, left_eye, nose
                )

            resp.append((detected_face, img_region, confidence, identity["landmarks"]))

    return resp


# This should be a replacement for functions.extract_faces()
# that also returns the landmarks. This will then be followed
# by stand-in code for the rest of DeepFace.represent()
def extract_face_regions(
    backend_model,
    img,
    align=True,
    enforce_detection=False,
    grayscale=False,
):
    extracted_faces = []

    img = functions.load_image(img)
    # Only used if no face sub-images are detected
    img_region = [0, 0, img.shape[1], img.shape[0]]

    target_size = functions.find_target_size(model_name=frontend_model_name)

    face_objs = detect_retinaface(backend_model, img, align)

    if len(face_objs) == 0 and enforce_detection is True:
        raise ValueError(
            "Face could not be detected. "
            " Please confirm that the picture is a face photo "
            + "or consider to set enforce_detection param to False."
        )

    if len(face_objs) == 0 and enforce_detection is False:
        face_objs = [(img, img_region, 0, {})]

    for current_img, current_region, confidence, landmarks in face_objs:
        if current_img.shape[0] > 0 and current_img.shape[1] > 0:
            if grayscale is True:
                current_img = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)

            # resize and padding
            if current_img.shape[0] > 0 and current_img.shape[1] > 0:
                factor_0 = target_size[0] / current_img.shape[0]
                factor_1 = target_size[1] / current_img.shape[1]
                factor = min(factor_0, factor_1)

                dsize = (
                    int(current_img.shape[1] * factor),
                    int(current_img.shape[0] * factor),
                )
                current_img = cv2.resize(current_img, dsize)

                diff_0 = target_size[0] - current_img.shape[0]
                diff_1 = target_size[1] - current_img.shape[1]
                if grayscale is False:
                    # Put the base image in the middle of the padded image
                    current_img = np.pad(
                        current_img,
                        (
                            (diff_0 // 2, diff_0 - diff_0 // 2),
                            (diff_1 // 2, diff_1 - diff_1 // 2),
                            (0, 0),
                        ),
                        "constant",
                    )
                else:
                    current_img = np.pad(
                        current_img,
                        (
                            (diff_0 // 2, diff_0 - diff_0 // 2),
                            (diff_1 // 2, diff_1 - diff_1 // 2),
                        ),
                        "constant",
                    )

            # double check: if target image is not still the same size with target.
            if current_img.shape[0:2] != target_size:
                current_img = cv2.resize(current_img, target_size)

            # normalizing the image pixels
            img_pixels = np.asarray(current_img, dtype="uint8")
            img_pixels = np.expand_dims(img_pixels, axis=0)
            img_pixels = img_pixels / 255

            # int cast is for the exception - object of type 'float32' is not
            # JSON serializable
            region_obj = {
                "x": round(float(current_region[0]), 2),
                "y": round(float(current_region[1]), 2),
                "w": round(float(current_region[2]), 2),
                "h": round(float(current_region[3]), 2),
            }

            extracted_face = [img_pixels, region_obj, confidence, landmarks]
            extracted_faces.append(extracted_face)

    if len(extracted_faces) == 0 and enforce_detection is True:
        raise ValueError(
            f"Detected face shape is {img.shape}. Consider to set enforce_detection arg to False."
        )

    return extracted_faces


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
        "--video-path",
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

    video_name = Path(args.video_path).name

    faces_path = Path("app", "labeled_face_images", video_name)
    if not os.path.isdir(faces_path):
        logging.error(f"No folder with labeled face images found be at {faces_path}")
        return

    face_files = [
        f
        for f in os.listdir(faces_path)
        if os.path.isfile(Path(faces_path, f))
        and Path(faces_path, f).suffix.lower() in [".png", ".jpg", ".jpeg", ".gif"]
    ]
    if not face_files:
        logging.error(f"No face images found in {faces_path}")

    frontend_model = DeepFace.build_model(frontend_model_name)
    backend_model = RetinaFace.build_model()

    cluster_id = 0
    file_to_detection = {}
    for f in face_files:
        face_image_path = Path(faces_path, f)

        face_image = cv2.imread(face_image_path, cv2.IMREAD_COLOR)

        img_objs = extract_face_regions(backend_model, face_image)

        if not len(img_objs):
            logging.info(f"Couldn't find a face in {f}")
            continue

        img, region, confidence, landmarks = img_objs[0]
        # custom normalization
        img = functions.normalize_input(img=img, normalization="base")
        embedding = frontend_model.predict(img)[0].tolist()

        face_bbox = [
            region["x"],
            region["y"],
            region["w"],
            region["h"],
        ]

        float_landmarks = {}
        for part in landmarks:
            float_coords = [round(float(num), 2) for num in landmarks[part]]
            float_landmarks[part] = float_coords

        file_to_detection[f] = {
            "bbox": face_bbox,
            "embedding": embedding,
            "landmarks": float_landmarks,
            "confidence": confidence,
            "cluster_id": cluster_id,
        }

        cluster_id += 1

    json.dump(
        file_to_detection,
        open(
            Path("app", "labeled_face_images", "cluster_id_to_image.txt"),
            "w",
            encoding="utf-8",
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())
