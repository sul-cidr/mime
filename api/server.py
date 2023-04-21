import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pose_data_db import PoseDataDatabase

mime_api = FastAPI(root_path=os.environ.get("PUBLIC_API_BASE", "/"))


mime_api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@mime_api.get("/")
async def root():
    return {"message": "MIME API"}


@mime_api.get("/videos/")
async def videos():
    db = await PoseDataDatabase.create(drop=False)
    videos = await db.get_available_videos()
    return {"videos": videos}


@mime_api.get("/poses/{video_id}/")
async def poses(video_id: int):
    db = await PoseDataDatabase.create(drop=False)
    pose_data_by_frame = await db.get_pose_data_by_frame(video_id)
    return pose_data_by_frame


if __name__ == "__main__":
    uvicorn.run("server:mime_api", host="0.0.0.0", port=5000, reload=True)
