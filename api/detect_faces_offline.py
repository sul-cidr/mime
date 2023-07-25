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
import pandas as pd
from deepface import DeepFace
from rich.logging import RichHandler


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

    output_path = f"{video_path}.faces.jsonl"

    if os.path.exists(output_path) and not args.overwrite:
        logging.error(
            f"Output file {output_path} already exists and --overwrite not specified. Exiting."
        )
        return

    video_name = video_path.name

    logging.info(f"Running face detection on video {video_name}")

    cap = cv2.VideoCapture(str(video_path))
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    def image_from_video_frame(video_file, frameno):
        """Grab the specified frame from the video and converts it into an RGBA array"""
        cap = cv2.VideoCapture(video_file)
        cap.set(1, frameno)
        ret, img = cap.read()
        # rgb_bg = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        # img = cv2.cvtColor(rgb_bg, cv2.COLOR_RGB2RGBA)
        # image = np.asarray(img)
        # cap.release()
        # return image
        return img

    with jsonlines.open(output_path, mode="a") as writer:
        for frameno in range(video_frames):
            output_json = []
            img = image_from_video_frame(str(video_path), frameno)
            face_vectors = []
            try:
                face_vectors = DeepFace.represent(
                    img,
                    model_name="DeepFace",
                    enforce_detection=True,
                    detector_backend="retinaface",
                )
            except Exception as ex:
                logging.info(
                    f"Unable to find faces in tracked pose frame {frameno + 1}"
                )
                continue

            for face_vector in face_vectors:
                face_bbox = [
                    face_vector["facial_area"]["x"],
                    face_vector["facial_area"]["y"],
                    face_vector["facial_area"]["w"],
                    face_vector["facial_area"]["h"],
                ]
                output_json.append(
                    {
                        "frame": frameno + 1,
                        "bbox": face_bbox,
                        "embedding": face_vector["embedding"],
                    }
                )
            logging.info(f"found {len(face_vectors)} faces in frame {frameno+1}")

            # with open(output_path, "w", encoding="utf-8") as out_file:
            #     json.dump(output_json, out_file, indent=2)
            writer.write_all(output_json)


if __name__ == "__main__":
    asyncio.run(main())
