import json
import logging
import os
from pathlib import Path
from uuid import UUID

import cv2
import imageio.v3 as iio
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utils.timing import add_timing_middleware

from lib.json_encoder import MimeJSONEncoder
from mime_db import MimeDb

load_dotenv()
VIDEO_SRC_FOLDER = os.getenv("VIDEO_SRC_FOLDER")

try:
    assert VIDEO_SRC_FOLDER
except AssertionError:
    raise SystemExit("Error: VIDEO_SRC_FOLDER is required") from None


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
    video = await request.app.state.db.get_video_by_id(video_id)
    video_path = f"/videos/{video['video_name']}"
    img = iio.imread(video_path, index=frame - 1, plugin="pyav")
    Path(f"/static/{video_id}/frames").mkdir(parents=True, exist_ok=True)
    iio.imwrite(f"/static/{video_id}/frames/{frame}.jpeg", img, extension=".jpeg")
    return Response(
        content=iio.imwrite("<bytes>", img, extension=".jpeg"),
        media_type="image/jpeg",
    )


@mime_api.get("/frame/{video_id}/{frame}/{xywh}/")
async def get_frame_region(video_id: UUID, frame: int, xywh: str, request: Request):
    video = await request.app.state.db.get_video_by_id(video_id)
    video_path = f"/videos/{video['video_name']}"
    x, y, w, h = [round(float(elt)) for elt in xywh.split(",")]
    img = iio.imread(video_path, index=frame - 1, plugin="pyav")
    img_region = img[y : y + h, x : x + w]
    return Response(
        content=iio.imwrite("<bytes>", img_region, extension=".jpeg"),
        media_type="image/jpeg",
    )


@mime_api.get("/frame/resize/{video_id}/{frame}/{xywh_resize}/")
async def get_frame_region_resized(
    video_id: UUID, frame: int, xywh_resize: str, request: Request
):
    video = await request.app.state.db.get_video_by_id(video_id)
    video_path = f"/videos/{video['video_name']}"
    xywh, resize_dims = xywh_resize.split("|")
    x, y, w, h = [round(float(elt)) for elt in xywh.split(",")]
    img = iio.imread(video_path, index=frame - 1, plugin="pyav")
    img_region = img[y : y + h, x : x + w]
    rw, rh = [round(float(elt)) for elt in resize_dims.split(",")]
    if rw is not None and rh is not None:
        resized_region = cv2.resize(img_region, (rw, rh))
    elif rw is not None and rh is None:
        resized_region = cv2.resize(img_region, (rw, h))
    elif rw is None and rh is not None:
        resized_region = cv2.resize(img_region, (w, rh))
    return Response(
        content=iio.imwrite("<bytes>", resized_region, extension=".jpeg"),
        media_type="image/jpeg",
    )


@mime_api.get("/pose_cluster_image/{video_name}/{cluster_id}/")
async def get_pose_cluster_image(video_name: str, cluster_id: int, request: Request):
    image_path = f"/app/pose_cluster_images/{video_name}/{cluster_id}.png"
    img = iio.imread(image_path)
    return Response(
        content=iio.imwrite("<bytes>", img, extension=".png"),
        media_type="image/png",
    )


@mime_api.get("/poses/{video_id}/")
async def poses(video_id: UUID, request: Request):
    frame_data = await request.app.state.db.get_pose_data_by_frame(video_id)
    return Response(
        content=json.dumps(frame_data, cls=MimeJSONEncoder),
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


@mime_api.get("/poses/similar/{metric}/{video_id}/{frame}/{pose_idx}/")
async def get_nearest_poses(
    metric: str, video_id: UUID, frame: int, pose_idx: int, request: Request
):
    frame_data = await request.app.state.db.get_nearest_poses(
        video_id, frame, pose_idx, metric
    )
    return Response(
        content=json.dumps(frame_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


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


@mime_api.get("/movelets/similar/{metric}/{video_id}/{frame}/{track_id}/")
async def get_nearest_movelets(
    metric: str, video_id: UUID, frame: int, track_id: int, request: Request
):
    movelet_data = await request.app.state.db.get_nearest_movelets(
        video_id, frame, track_id, metric
    )
    return Response(
        content=json.dumps(movelet_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


if __name__ == "__main__":
    uvicorn.run("server:mime_api", host="0.0.0.0", port=5000, reload=True)
