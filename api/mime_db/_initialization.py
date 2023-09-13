import logging


async def initialize_db(conn, drop=False) -> None:
    if drop:
        logging.warn("Dropping database tables...")
        await conn.execute("DROP TABLE IF EXISTS video CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS pose CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS movelet CASCADE;")

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS video (
            id uuid DEFAULT uuid_generate_v1mc() PRIMARY KEY,
            video_name VARCHAR(150) UNIQUE NOT NULL,
            frame_count INTEGER NOT NULL,
            fps FLOAT NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            created_on TIMESTAMP NOT NULL DEFAULT NOW()
        )
        ;
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pose (
            video_id uuid NOT NULL REFERENCES video(id) ON DELETE CASCADE,
            frame INTEGER NOT NULL,
            pose_idx INTEGER NOT NULL,
            keypoints vector(51) NOT NULL,
            bbox FLOAT[4] NOT NULL,
            score FLOAT NOT NULL,
            category INTEGER,
            track_id INTEGER DEFAULT NULL,
            PRIMARY KEY(video_id, frame, pose_idx)
        )
        ;
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS face (
            video_id uuid NOT NULL REFERENCES video(id) ON DELETE CASCADE,
            frame INTEGER NOT NULL,
            pose_idx INTEGER,
            bbox FLOAT[4] NOT NULL,
            confidence FLOAT NOT NULL,
            landmarks vector(10) NOT NULL,
            embedding vector(4096) NOT NULL
        )
        ;
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS movelet (
            video_id uuid NOT NULL REFERENCES video(id) ON DELETE CASCADE,
            track_id INTEGER NOT NULL,
            tick INTEGER NOT NULL,
            start_frame INTEGER NOT NULL,
            end_frame INTEGER NOT NULL,
            pose_idx INTEGER NOT NULL,
            start_timecode FLOAT NOT NULL,
            end_timecode FLOAT NOT NULL,
            prev_norm vector(34) NOT NULL,
            norm vector(34) NOT NULL,
            motion vector(68) NOT NULL,
            movement FLOAT DEFAULT 0,
            PRIMARY KEY(video_id, track_id, tick)
        )
        ;
        """
    )

    # consider DROP IF EXISTS to recreate the index from scratch every time the DB
    #  is initialized (protects against future changes at minimal cost?)
    await conn.execute(
        """
        DROP MATERIALIZED VIEW IF EXISTS video_meta;
        DROP INDEX IF EXISTS video_meta_id_idx;

        CREATE MATERIALIZED VIEW IF NOT EXISTS video_meta AS
            SELECT video.*,
                COUNT(pose) AS pose_ct,
                COUNT(DISTINCT pose.track_id) AS track_ct,
                TRUNC(COUNT(pose)::decimal / video.frame_count, 2) AS poses_per_frame,
                COUNT(face) AS face_ct
            FROM video
                LEFT JOIN pose ON video.id = pose.video_id
                LEFT JOIN face ON video.id = face.video_id
            GROUP BY video.id
            ORDER BY video_name
        WITH DATA
        ;

        CREATE UNIQUE INDEX IF NOT EXISTS video_meta_id_idx ON video_meta (id);
        """
    )
