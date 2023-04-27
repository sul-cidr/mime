import json
import os

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from json_encoder import MimeJSONEncoder
from pose_data_db import PoseDataDatabase

mime_api = FastAPI(root_path=os.environ.get("PUBLIC_API_BASE", "/"))


mime_api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@mime_api.on_event("startup")
async def startup():
    mime_api.state.db = await PoseDataDatabase.create(drop=False)


@mime_api.get("/")
async def root():
    return {"message": "MIME API"}


@mime_api.get("/videos/")
async def videos(request: Request):
    videos = await request.app.state.db.get_available_videos()
    return {"videos": videos}


@mime_api.get("/poses/{video_id}/")
async def poses(video_id: int, request: Request):
    pose_data_by_frame = await request.app.state.db.get_pose_data_by_frame(video_id)
    return pose_data_by_frame


@mime_api.get("/poses/{video_id}/{frame}/")
async def poses_by_frame(video_id: int, frame: int, request: Request):
    frame_data = await request.app.state.db.get_frame_data(video_id, frame)
    return Response(
        content=json.dumps(frame_data, cls=MimeJSONEncoder),
        media_type="application/json",
    )


if __name__ == "__main__":
    uvicorn.run("server:mime_api", host="0.0.0.0", port=5000, reload=True)
