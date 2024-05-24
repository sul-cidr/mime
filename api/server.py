import json
import logging
import os
from pathlib import Path
from typing import Literal, Set
from uuid import UUID

import cv2
import imageio.v3 as iio
import numpy as np
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utils.timing import add_timing_middleware

from lib.json_encoder import MimeJSONEncoder
from lib.pose_drawing import pad_and_excerpt_image
from lib.pose_utils import get_poem_embedding
from mime_db import MimeDb

load_dotenv()
VIDEO_SRC_FOLDER = os.getenv("VIDEO_SRC_FOLDER")
CACHE_FOLDER = os.getenv("CACHE_FOLDER")

try:
    assert VIDEO_SRC_FOLDER
except AssertionError:
    raise SystemExit("Error: VIDEO_SRC_FOLDER is required") from None

try:
    assert CACHE_FOLDER
except AssertionError:
    raise SystemExit("Error: CACHE_FOLDER is required") from None


logging.basicConfig(level=(os.getenv("LOG_LEVEL") or "INFO").upper())
logger = logging.getLogger(__name__)

mime_api = FastAPI(root_path=os.environ.get("PUBLIC_API_BASE", "/"))
add_timing_middleware(mime_api, record=logger.debug, prefix="api")


mime_api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_frame_image(video_id: UUID, frame: int, request: Request) -> np.ndarray:
    frame_image = Path(CACHE_FOLDER, str(video_id), "frames", f"{frame}.jpeg")
    if frame_image.exists():
        return iio.imread(frame_image)
    else:
        video = await request.app.state.db.get_video_by_id(video_id)
        video_path = f"/videos/{video['video_name']}"
        return iio.imread(video_path, index=frame - 1, plugin="pyav")


@mime_api.on_event("startup")
async def startup():
    mime_api.state.db = await MimeDb.create(drop=False)


@mime_api.get("/")
async def root():
    return {"message": "MIME API"}


@mime_api.get("/videos/")
async def videos(request: Request):
    available_videos = await request.app.state.db.get_available_videos()
    return {"videos": available_videos}


@mime_api.get("/frame/{video_id}/{frame}/")
async def get_frame(video_id: UUID, frame: int, request: Request):
    img = await get_frame_image(video_id, frame, request)
    return Response(
        content=iio.imwrite("<bytes>", img, extension=".jpeg"),
        media_type="image/jpeg",
    )


@mime_api.get("/frame/excerpt/{video_id}/{frame}/{xywh}/")
async def get_frame_region(video_id: UUID, frame: int, xywh: str, request: Request):
    img = await get_frame_image(video_id, frame, request)
    x, y, w, h = [round(float(elt)) for elt in xywh.split(",")]
    img_region = pad_and_excerpt_image(img, x, y, w, h)
    return Response(
        content=iio.imwrite("<bytes>", img_region, extension=".jpeg"),
        media_type="image/jpeg",
    )


@mime_api.get("/frame/resize/{video_id}/{frame}/{xywh_resize}/")
async def get_frame_region_resized(
    video_id: UUID, frame: int, xywh_resize: str, request: Request
):
    img = await get_frame_image(video_id, frame, request)
    xywh, resize_dims = xywh_resize.split("|")
    x, y, w, h = [round(float(elt)) for elt in xywh.split(",")]
    img_region = pad_and_excerpt_image(img, x, y, w, h)
    rw, rh = [round(float(elt)) for elt in resize_dims.split(",")]
    if rw is not None and rh is not None:
        resized_region = cv2.resize(img_region, (rw, rh))
    elif rw is not None and rh is None:
        resized_region = cv2.resize(img_region, (rw, h))
    elif rw is None and rh is not None:
        resized_region = cv2.resize(img_region, (w, rh))
    else:
        raise ValueError("Invalid resize dimensions specified")
    return Response(
        content=iio.imwrite("<bytes>", resized_region, extension=".jpeg"),
        media_type="image/jpeg",
    )


@mime_api.get("/pose_cluster_image/{video_name}/{cluster_id}/")
async def get_pose_cluster_image(video_name: str, cluster_id: int):
    image_path = f"/app/pose_cluster_images/{video_name}/{cluster_id}.png"
    img = iio.imread(image_path)
    return Response(
        content=iio.imwrite("<bytes>", img, extension=".png"),
        media_type="image/png",
    )


@mime_api.get("/face_image/{video_name}/{image_fn}/")
async def get_face_image(video_name: str, image_fn: str):
    image_path = f"/app/face_images/{video_name}/{image_fn}"
    img = iio.imread(image_path)
    return Response(
        content=iio.imwrite("<bytes>", img, extension=".png"),
        media_type="image/png",
    )


@mime_api.get("/labeled_face_data/{video_name}/")
async def get_labeled_face_data(video_name: str):
    json_path = f"/app/face_images/{video_name}/cluster_id_to_image.json"
    # it probably isn't necessary to round-trip text-json-text, but maybe this
    # provides some kind of santitization?
    json_data = {}
    if os.path.isfile(json_path):
        with open(json_path, "r", encoding="utf-8") as json_file:
            json_data = json.load(json_file)
    return Response(
        content=json.dumps(json_data),
        media_type="application/json",
    )


@mime_api.get("/frame_track_pose/{video_id}/{frameno}/{track_id}")
async def pose(video_id: UUID, frameno: int, track_id: int, request: Request):
    pose_data = await request.app.state.db.get_pose_by_frame_and_track(
        video_id, frameno, track_id
    )
    return Response(
        content=json.dumps(pose_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


@mime_api.get("/frame_track_face/{video_id}/{frameno}/{track_id}")
async def face(video_id: UUID, frameno: int, track_id: int, request: Request):
    pose_data = await request.app.state.db.get_face_by_frame_and_track(
        video_id, frameno, track_id
    )
    return Response(
        content=json.dumps(pose_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


@mime_api.get("/poses/{video_id}/")
async def poses(video_id: UUID, request: Request):
    frame_data = Path(CACHE_FOLDER, str(video_id), "pose_data_by_frame.json")
    if frame_data.exists():
        with frame_data.open("r", encoding="utf-8") as _fh:
            frame_data = _fh.read()
    else:
        frame_data = await request.app.state.db.get_pose_data_by_frame(video_id)
        frame_data = json.dumps(frame_data, cls=MimeJSONEncoder)
        cache_dir = Path(CACHE_FOLDER, str(video_id))
        cache_dir.mkdir(parents=True, exist_ok=True)
        with (cache_dir / "pose_data_by_frame.json").open("w") as _fh:
            _fh.write(frame_data)

    return Response(
        content=frame_data,
        media_type="application/json",
    )


@mime_api.get("/shots/{video_id}/")
async def shots(video_id: UUID, request: Request):
    shot_data = await request.app.state.db.get_video_shot_boundaries(video_id)
    return Response(
        content=json.dumps(shot_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


@mime_api.get("/poses/{video_id}/{frame}/")
async def poses_by_frame(video_id: UUID, frame: int, request: Request):
    frame_data = await request.app.state.db.get_frame_data(video_id, frame)
    return Response(
        content=json.dumps(frame_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


@mime_api.get("/clustered_faces/{video_id}/")
async def clustered_faces(video_id: UUID, request: Request):
    frame_data = await request.app.state.db.get_clustered_face_data_from_video(video_id)
    return Response(
        content=json.dumps(frame_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


@mime_api.get("/clustered_poses/{video_id}/")
async def clustered_poses(video_id: UUID, request: Request):
    frame_data = await request.app.state.db.get_clustered_movelet_data_from_video(
        video_id
    )
    return Response(
        content=json.dumps(frame_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


@mime_api.get("/faces/{video_id}/{frame}/")
async def faces_by_frame(video_id: UUID, frame: int, request: Request):
    frame_data = await request.app.state.db.get_frame_faces(video_id, frame)
    return Response(
        content=json.dumps(frame_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


# compares a known pose from the DB to others in the DB (c.f. "search_nearest_")
@mime_api.get(
    "/poses/similar/{max_results}/{metric_and_max}/{video_param}/{frame}/{pose_idx}/{avoid_shot}/"
)
async def get_nearest_poses(
    max_results: int,
    metric_and_max: str,
    video_param: UUID | str,
    frame: int,
    pose_idx: int,
    avoid_shot: int,
    request: Request,
):
    metric, max_distance = metric_and_max.split("|")

    embedding = "norm"
    if metric == "view_invariant":
        metric = "cosine"
        embedding = "poem_embedding"
    elif metric == "global":
        metric = "cosine"
        embedding = "global3d_coco13"

    frame_data = await request.app.state.db.get_nearest_poses(
        video_param,
        frame,
        pose_idx,
        metric,
        embedding,
        float(max_distance),
        avoid_shot,
        max_results,
    )

    return Response(
        content=json.dumps(frame_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


# searches the DB for similar poses to pose coords from webcam or other source
@mime_api.get("/poses/similar/{max_results}/{metric_and_max}/{video_param}/{coords}/")
async def search_nearest_poses(
    max_results: int,
    metric_and_max: str,
    video_param: UUID | str,
    coords: str,
    request: Request,
):
    metric, max_distance = metric_and_max.split("|")

    if metric == "global":
        pose_coords = list(map(float, coords.split(",")))
    else:
        pose_coords = list(map(int, coords.split(",")))

    query_pose = pose_coords

    embedding = "norm"
    if metric == "view_invariant":
        metric = "cosine"
        embedding = "poem_embedding"
        query_pose = get_poem_embedding(pose_coords)
    elif metric == "global":
        metric = "cosine"
        embedding = "global3d_coco13"

    frame_data = await request.app.state.db.search_by_pose(
        video_param,
        query_pose,
        metric,
        embedding,
        float(max_distance),
        max_results,
    )

    return Response(
        content=json.dumps(frame_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


@mime_api.get(
    "/actions/similar/{max_results}/{metric_and_max}/{video_param}/{frame}/{track_id}/{avoid_shot}/"
)
async def get_nearest_actions(
    max_results: int,
    metric_and_max: str,
    video_param: UUID | str,
    frame: int,
    track_id: int,
    avoid_shot: int,
    request: Request,
):
    # metric is probably always cosine
    _, max_distance = metric_and_max.split("|")

    frame_data = await request.app.state.db.get_nearest_actions(
        video_param,
        frame,
        track_id,
        float(max_distance),
        avoid_shot,
        max_results,
    )

    return Response(
        content=json.dumps(frame_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


# XXX Movelets search functions probably will be removed soon, so not maintained
@mime_api.get("/movelets/pose/{video_id}/{frame}/{track_id}/")
async def get_movelet_from_pose(
    video_id: UUID, frame: int, track_id: int, request: Request
):
    movelet_data = await request.app.state.db.get_movelet_from_pose(
        video_id, frame, track_id
    )
    return Response(
        content=json.dumps(movelet_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


@mime_api.get(
    "/movelets/similar/{max_results}/{metric_and_max}/{video_id}/{frame}/{track_id}/{avoid_shot}/"
)
async def get_nearest_movelets(
    max_results: int,
    metric_and_max: str,
    video_id: UUID,
    frame: int,
    track_id: int,
    avoid_shot: int,
    request: Request,
):
    metric, max_distance = metric_and_max.split("|")

    movelet_data = await request.app.state.db.get_nearest_movelets(
        video_id, frame, track_id, metric, float(max_distance), avoid_shot, max_results
    )
    return Response(
        content=json.dumps(movelet_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


@mime_api.get("/pose-search/")
async def pose_search(
    request: Request,
    pose: str,
    search_type: Literal["cosine", "euclidean", "view_invariant", "3d"] = "cosine",
    videos: Set[str] = Query(None),  # noqa: B008
    limit: int = 50,
    exclude_within_frames: int = 30,
):
    results = await request.app.state.db.search_poses(
        pose_coords=pose,
        search_type=search_type,
        videos=videos,
        limit=limit,
        exclude_within_frames=exclude_within_frames,
    )
    return Response(
        content=json.dumps(results, cls=MimeJSONEncoder),
        media_type="application/json",
    )


if __name__ == "__main__":
    uvicorn.run("server:mime_api", host="0.0.0.0", port=5000, reload=True)
