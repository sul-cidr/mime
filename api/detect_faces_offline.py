#!/usr/bin/env python3

"""CLI to run face detection on a video file and write the output to a JSON file."""

import argparse
import asyncio
import logging
import os
from pathlib import Path

import cv2
import jsonlines
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
            "Face could not be detected. Please confirm that the picture is a face photo "
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

            # int cast is for the exception - object of type 'float32' is not JSON serializable
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
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing file",
    )

    parser.add_argument("--video-path", action="store", required=True)

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    # This should really just be the name of the video, since its pose data
    # should already be in the DB by the time this is run
    video_path = Path(args.video_path)

    output_path = f"{video_path}.faces.{frontend_model_name}.jsonl"

    start_frame = 0

    if os.path.exists(output_path) and not args.overwrite:
        logging.info(
            f"Output file {output_path} already exists and --overwrite not specified, will append output for any remaining unprocessed frames."
        )
        with jsonlines.open(output_path) as reader:
            for line in reader:
                start_frame = line["frame"] + 1
        logging.info(
            f"Starting at frame {start_frame}."
        )
        last_line = ""
        with open(output_path, "r", encoding="utf-8") as outf:
            for line in outf:
                pass
            last_line = line
        if "\n" not in last_line:
            logging.info(
                "Adding newline to end of output file so appending new JSON lines works properly"
            )
            with open(output_path, "a", encoding="utf-8") as outf:
                outf.write("\n")

    video_name = video_path.name

    logging.info(f"Running face detection on video {video_name}")

    cap = cv2.VideoCapture(str(video_path))
    cap.get(cv2.CAP_PROP_FPS)
    int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    def image_from_video_frame(video_file, frameno):
        """Grab the specified frame from the video and converts it into an RGBA array"""
        cap = cv2.VideoCapture(video_file)
        cap.set(1, frameno)
        ret, img = cap.read()
        return img

    frontend_model = DeepFace.build_model(frontend_model_name)

    backend_model = RetinaFace.build_model()

    with jsonlines.open(output_path, mode="a") as writer:
        for frameno in range(start_frame, video_frames):
            output_json = []
            img = image_from_video_frame(str(video_path), frameno)
            img_objs = extract_face_regions(backend_model, img)

            # for face_vector in face_vectors:
            for img, region, confidence, landmarks in img_objs:
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

                output_json.append(
                    {
                        "frame": frameno + 1,
                        "bbox": face_bbox,
                        "embedding": embedding,
                        "landmarks": float_landmarks,
                        "confidence": confidence,
                    }
                )
            logging.info(f"found {len(img_objs)} faces in frame {frameno+1}")
            writer.write_all(output_json)


if __name__ == "__main__":
    asyncio.run(main())
