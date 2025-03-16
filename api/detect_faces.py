#!/usr/bin/env python3

"""CLI to run face detection on a video file and write the output to a JSON file."""

import argparse
import asyncio
import logging
import os
from pathlib import Path

import cv2
import jsonlines
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

    output_path = f"{video_path}.faces.{FRONTEND_MODEL_NAME}.jsonl"

    start_frame = 0

    if os.path.exists(output_path) and not args.overwrite:
        logging.info(
            f"Output file {output_path} already exists and --overwrite not specified, will append output for any remaining unprocessed frames."
        )
        with jsonlines.open(output_path) as reader:
            for line in reader:
                start_frame = line["frame"] + 1
        logging.info(f"Starting at frame {start_frame}.")
        last_line = ""
        with open(output_path, "r", encoding="utf-8") as outf:
            for line in outf:
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

    frontend_model = DeepFace.build_model(FRONTEND_MODEL_NAME)
    backend_model = RetinaFace.build_model()

    with jsonlines.open(output_path, mode="a") as writer:
        for frameno in range(start_frame, video_frames):
            output_json = []
            img = image_from_video_frame(str(video_path), frameno)
            img_objs = extract_face_regions(backend_model, frontend_model, img)

            # for face_vector in face_vectors:
            for img, region, confidence, landmarks in img_objs:
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
