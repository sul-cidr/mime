import json
import logging
import os
from uuid import UUID

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
    videos = await request.app.state.db.get_available_videos()
    return {"videos": videos}


@mime_api.get("/frame/{video_id}/{frame}/")
async def get_frame(video_id: UUID, frame: int, request: Request):
    video = await request.app.state.db.get_video_by_id(video_id)
    video_path = f"/videos/{video['video_name']}"
    img = iio.imread(video_path, index=frame - 1, plugin="pyav")
    return Response(
        content=iio.imwrite("<bytes>", img, extension=".jpeg"),
        media_type="image/jpeg",
    )


@mime_api.get("/poses/{video_id}/")
async def poses(video_id: UUID, request: Request):
    frame_data = await request.app.state.db.get_pose_data_by_frame(video_id)
    return Response(
        content=json.dumps(frame_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


@mime_api.get("/poses/{video_id}/{frame}/")
async def poses_by_frame(video_id: UUID, frame: int, request: Request):
    frame_data = await request.app.state.db.get_frame_data(video_id, frame)
    return Response(
        content=json.dumps(frame_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


@mime_api.get("/poses/similar/{metric}/{video_id}/{frame}/{pose_idx}/")
async def get_nearest_neighbors(
    metric: str, video_id: UUID, frame: int, pose_idx: int, request: Request
):
    frame_data = await request.app.state.db.get_nearest_neighbors(
        video_id, frame, pose_idx, metric
    )
    return Response(
        content=json.dumps(frame_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


if __name__ == "__main__":
    uvicorn.run("server:mime_api", host="0.0.0.0", port=5000, reload=True)
