"""MimeDb class to abstract out the database interaction."""

import logging
import os

import asyncpg
from dotenv import load_dotenv
from pgvector.asyncpg import register_vector

logging.getLogger("dotenv.main").setLevel(logging.FATAL)
load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

try:
    assert all((DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT))
except AssertionError:
    raise SystemExit(
        "Error: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT are all required"
    ) from None


class MimeDb:
    """Class to interact with the database."""

    from mime_db._data_loading import (
        add_frame_movement,
        add_pose_faces,
        add_shot_boundaries,
        add_video,
        add_video_faces,
        add_video_movelets,
        add_video_tracks,
        annotate_pose,
        assign_face_clusters_by_track,
        assign_frame_interest,
        assign_movelet_clusters,
        assign_poem_embeddings,
        assign_pose_interest,
        clear_actions,
        clear_poses,
        load_4dh_predictions,
        load_lart_predictions,
        load_openpifpaf_predictions,
    )
    from mime_db._initialization import initialize_db, remove_video
    from mime_db._pose_search import search_poses
    from mime_db._read_only import (
        get_available_videos,
        get_clustered_face_data_from_video,
        get_clustered_movelet_data_from_video,
        get_face_by_frame_and_track,
        get_frame_data,
        get_frame_data_range,
        get_frame_faces,
        get_movelet_data_from_video,
        get_movelet_from_pose,
        get_nearest_actions,
        get_nearest_movelets,
        get_nearest_poses,
        get_pose_by_frame_and_track,
        get_pose_data_by_frame,
        get_pose_data_from_video,
        get_poses_with_faces,
        get_track_frames,
        get_video_by_id,
        get_video_by_name,
        get_video_id,
        get_video_shot_boundaries,
        get_video_shots,
        search_by_pose,
    )

    _pool: asyncpg.Pool

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @classmethod
    async def create(cls, drop=False) -> "MimeDb":
        """Factory method to create a new MimeDb instance.
        Used because __init__ doesn't work well with async/await.
        """
        pool = await MimeDb.get_pool()

        async with pool.acquire() as conn:
            await MimeDb.initialize_db(conn, drop)

        return cls(pool)

    @staticmethod
    async def get_pool() -> asyncpg.Pool:
        pool = await asyncpg.create_pool(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            port=DB_PORT,
            setup=MimeDb.setup_connection,
        )
        if not pool:
            raise RuntimeError("Database connection could not be established")
        return pool

    @staticmethod
    async def get_connection() -> asyncpg.Connection:
        conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            port=DB_PORT,
        )
        await MimeDb.setup_connection(conn)
        return conn

    @staticmethod
    async def setup_connection(conn: asyncpg.Connection):
        await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        await register_vector(conn)
