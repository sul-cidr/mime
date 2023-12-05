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
        CREATE TABLE IF NOT EXISTS frame (
            video_id uuid NOT NULL REFERENCES video(id) ON DELETE CASCADE,
            frame INTEGER NOT NULL,
            local_shot_prob FLOAT NOT NULL,
            global_shot_prob FLOAT NOT NULL,
            is_shot_boundary BOOLEAN DEFAULT FALSE,
            total_movement FLOAT DEFAULT 0.0,
            PRIMARY KEY(video_id, frame)
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
            embedding vector(4096) NOT NULL,
            track_id INTEGER DEFAULT NULL,
            cluster_id INTEGER DEFAULT NULL
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
            cluster_id INTEGER DEFAULT NULL,
            PRIMARY KEY(video_id, track_id, tick)
        )
        ;
        """
    )

    await conn.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS video_meta AS
            SELECT video.*, pose_ct, track_ct, shot_ct, poses_per_frame, face_ct
            FROM video
            LEFT JOIN (
                SELECT video.id, COUNT(*) AS face_ct
                FROM video
                INNER JOIN face ON video.id = face.video_id
                GROUP BY video.id
            ) AS f ON video.id = f.id
            LEFT JOIN (
                SELECT video.id, COUNT(*) filter (where frame.is_shot_boundary) as shot_ct
                FROM video
                INNER JOIN frame ON video.id = frame.video_id
                GROUP BY video.id
            ) as s on video.id = s.id
            LEFT JOIN (
                SELECT video.id,
                    COUNT(*) AS pose_ct,
                    COUNT(DISTINCT pose.track_id) AS track_ct,
                    TRUNC(COUNT(*)::decimal / video.frame_count, 2) AS poses_per_frame
                FROM video
                INNER JOIN pose ON video.id = pose.video_id
                GROUP BY video.id
                ) AS p ON video.id = p.id
            ORDER BY video_name
        WITH DATA;

        CREATE UNIQUE INDEX ON video_meta (id);
        """
    )
