#!/usr/bin/env python3

"""CLI to run face detection on a video file and write the output to a JSON file."""

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path

import cv2
from deepface import DeepFace
from deepface.modules import preprocessing
from retinaface import RetinaFace
from rich.logging import RichHandler

from lib.deepface_utils import extract_face_regions

FRONTEND_MODEL_NAME = "ArcFace"  # "DeepFace" (could be a cmd line param)


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

    faces_path = Path("api", "face_images", video_name)
    if not os.path.isdir(faces_path):
        logging.error(f"No folder with labeled face images found at {faces_path}")
        return

    face_files = [
        f
        for f in os.listdir(faces_path)
        if os.path.isfile(Path(faces_path, f))
        and Path(faces_path, f).suffix.lower() in [".png", ".jpg", ".jpeg", ".gif"]
    ]
    if not face_files:
        logging.error(f"No face images found in {faces_path}")

    frontend_model = DeepFace.build_model(FRONTEND_MODEL_NAME)
    backend_model = RetinaFace.build_model()

    cluster_id = 0
    files_to_detections = []
    for f in face_files:
        face_image_path = Path(faces_path, f)

        face_image = cv2.imread(str(face_image_path), cv2.IMREAD_COLOR)

        img_objs = extract_face_regions(backend_model, frontend_model, face_image)

        if not len(img_objs):
            logging.info(f"Couldn't find a face in {f}")
            continue

        img, region, confidence, landmarks = img_objs[0]
        # custom normalization
        img = preprocessing.normalize_input(img=img, normalization="base")
        embedding = frontend_model.forward(img)

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

        files_to_detections.append(
            {
                f: {
                    "bbox": face_bbox,
                    "embedding": embedding,
                    "landmarks": float_landmarks,
                    "confidence": confidence,
                    "cluster_id": cluster_id,
                }
            }
        )

        cluster_id += 1

    with open(
        Path("api", "face_images", video_name, "cluster_id_to_image.json"),
        "w",
        encoding="utf-8",
    ) as faces_json:
        json.dump(files_to_detections, faces_json)


if __name__ == "__main__":
    asyncio.run(main())
