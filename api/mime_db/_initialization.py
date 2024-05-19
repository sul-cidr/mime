import logging


async def initialize_db(conn, drop=False) -> None:
    if drop:
        logging.warning("Dropping database tables...")
        await conn.execute("DROP TABLE IF EXISTS video CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS pose CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS movelet CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS face CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS frame CASCADE;")

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
            shot INTEGER DEFAULT 0,
            total_movement FLOAT DEFAULT 0.0,
            pose_interest FLOAT DEFAULT 0.0,
            action_interest FLOAT DEFAULT 0.0,
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
            keypoints vector(39) NOT NULL,
            norm vector(26) DEFAULT NULL,
            keypointsopp vector(51) DEFAULT NULL,
            keypoints4dh vector(135) DEFAULT NULL,
            keypoints3d vector(39) DEFAULT NULL,
            global3d_phalp vector(135) DEFAULT NULL,
            global3d_coco_13 vector(39) DEFAULT NULL,
            ava_action vector(60) DEFAULT NULL,
            action_labels text[3] DEFAULT NULL,
            bbox FLOAT[4] NOT NULL,
            camera FLOAT[3] NOT NULL,
            score FLOAT NOT NULL,
            category INTEGER,
            track_id INTEGER DEFAULT NULL,
            pose_interest FLOAT DEFAULT 0.0,
            action_interest FLOAT DEFAULT 0.0,
            poem_embedding vector(16) DEFAULT NULL,
            norm vector(26) DEFAULT NULL,
            global3d_coco13 vector(39) DEFAULT NULL,
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
            embedding vector(512) NOT NULL,
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
            prev_norm vector(26) NOT NULL,
            norm vector(26) NOT NULL,
            motion vector(52) NOT NULL,
            movement FLOAT DEFAULT 0,
            poem_embedding vector(16) DEFAULT NULL,
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

    await conn.execute(
        """
        CREATE MATERIALIZED VIEW if not exists video_frame_meta as
        SELECT  pose_faces.video_id,
                pose_faces.frame,
                pose_faces.track_ct,
                pose_faces.face_ct,
                pose_faces.avg_score,
                CAST(frame.is_shot_boundary AS INT) AS is_shot,
                frame.pose_interest,
                frame.action_interest,
                CASE
                  WHEN frame.total_movement = 'NaN'
                  THEN 0.0
                  ELSE ROUND(frame.total_movement::numeric, 2)
                END AS "movement"
        FROM (
            SELECT pose.video_id,
                   pose.frame,
                   count(NULLIF(pose.track_id,0)) AS track_ct,
                   count(face.pose_idx) AS face_ct,
                   ROUND(AVG(pose.score)::numeric, 2) AS avg_score
            FROM pose
            LEFT JOIN face ON
                pose.video_id = face.video_id AND
                pose.frame = face.frame AND
                pose.pose_idx = face.pose_idx
            GROUP BY pose.video_id, pose.frame
            ORDER BY pose.frame
        ) AS pose_faces
        LEFT JOIN frame ON
            pose_faces.video_id = frame.video_id AND
            pose_faces.frame = frame.frame
        ORDER BY pose_faces.frame
        WITH DATA;

        CREATE INDEX ON video_frame_meta (video_id);
        """
    )


# XXX Maybe shouldn't call this file _initialization if this will be here
async def remove_video(self, video_id) -> None:
    async with self._pool.acquire() as conn:
        logging.warning("Removing database entries associated with video")
        await conn.execute("DELETE FROM video WHERE id=$1", video_id)
