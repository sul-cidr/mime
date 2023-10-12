#!/usr/bin/env python3

"""CLI to run face detection on a video file and write the output to a JSON file."""

import argparse
import asyncio
import logging
import pickle
from pathlib import Path

try:
    import ffmpeg
except ModuleNotFoundError:
    raise ModuleNotFoundError(
        "For `predict_video` function `ffmpeg` needs to be installed in order to extract "
        "individual frames from video file. Install `ffmpeg` command line tool and then "
        "install python wrapper by `pip install ffmpeg-python`."
    )
import numpy as np

# Using TransNetV2 (https://github.com/soCzech/TransNetV2/tree/master/inference)
from lib.transnetv2.transnetv2 import TransNetV2
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

    model = TransNetV2()

    output_path = f"{video_path}.shots.TransNetV2.pkl"

    # XXX The reference implementation at
    # https://github.com/soCzech/TransNetV2/blob/master/inference/transnetv2.py
    # often produces differing frame counts from what OpenCV reads from the video,
    # unless the vsync="passthrough" option is added.
    #

    video_stream, err = (
        ffmpeg.input(video_path)
        .output(
            "pipe:", format="rawvideo", pix_fmt="rgb24", s="48x27", vsync="passthrough"
        )
        .run(capture_stdout=True, capture_stderr=True)
    )

    video = np.frombuffer(video_stream, np.uint8).reshape([-1, 27, 48, 3])
    # This returns two lists of scene boundary predictions for each frame, based
    # on individual frame thresholding and a full-video model. The reference
    # implementation only considers the latter when setting scene boundaries,
    # using a default threshold of 0.5.
    predictions = model.predict_frames(video)

    pickle.dump(predictions, open(output_path, "wb"))


if __name__ == "__main__":
    asyncio.run(main())
