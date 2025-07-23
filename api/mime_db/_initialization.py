import logging


async def initialize_db(conn, drop=False) -> None:
    if drop:
        logging.warning("Dropping database tables...")
        await conn.execute("DROP TABLE IF EXISTS video CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS frame CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS pose CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS face CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS hand CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS movelet CASCADE;")
        await conn.execute("DROP MATERIALIZED VIEW IF EXISTS video_meta CASCADE;")
        await conn.execute("DROP MATERIALIZED VIEW IF EXISTS video_meta_frame CASCADE;")

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS video (
            id uuid DEFAULT uuid_generate_v1mc() PRIMARY KEY,
            video_name VARCHAR(150) UNIQUE NOT NULL,
            frame_count INTEGER NOT NULL,
            fps FLOAT NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            scaled_width INTEGER NOT NULL,
            scaled_height INTEGER NOT NULL,
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
            total_movement3d FLOAT DEFAULT 0.0,
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
            global3d_coco13 vector(39) DEFAULT NULL,
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
            PRIMARY KEY(video_id, frame, pose_idx)
        )
        ;

        CREATE INDEX IF NOT EXISTS pose_poem_embedding_idx ON pose
          USING ivfflat (poem_embedding vector_cosine_ops);
        CREATE INDEX IF NOT EXISTS pose_ava_action_idx ON pose
          USING ivfflat (ava_action vector_cosine_ops);
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
        CREATE TABLE IF NOT EXISTS hand (
            video_id uuid NOT NULL REFERENCES video(id) ON DELETE CASCADE,
            frame INTEGER NOT NULL,
            pose_idx INTEGER DEFAULT NULL,
            hand_personid INTEGER,
            bbox FLOAT[4] NOT NULL,
            is_right BOOLEAN DEFAULT TRUE,
            confidence FLOAT NOT NULL DEFAULT 1.0,
            camera FLOAT[3] NOT NULL,
            camera_transform FLOAT[3] NOT NULL,
            keypoints2d vector(42) NOT NULL,
            keypoints3d vector(63) NOT NULL,
            global_orient FLOAT[9] NOT NULL,
            joint_angles3d vector(21) DEFAULT NULL,
            class_weights vector(7) DEFAULT NULL,
            rectified3d vector(63) DEFAULT NULL,
            track_id INTEGER DEFAULT NULL,
            cluster_id INTEGER DEFAULT NULL
        )
        ;

        CREATE INDEX IF NOT EXISTS hand_joint_angles3d_idx ON hand
          USING ivfflat (joint_angles3d vector_cosine_ops);
        CREATE INDEX IF NOT EXISTS hand_class_weights_idx ON hand
          USING ivfflat (class_weights vector_cosine_ops);
        CREATE INDEX IF NOT EXISTS hand_rectified3d_idx ON hand
          USING ivfflat (rectified3d vector_cosine_ops);
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
            prev_norm vector(26) NOT NULL,
            norm vector(26) NOT NULL,
            motion vector(52) NOT NULL,
            movement FLOAT DEFAULT 0,
            movement3d FLOAT DEFAULT 0,
            poem_embedding vector(16) DEFAULT NULL,
            cluster_id INTEGER DEFAULT NULL,
            PRIMARY KEY(video_id, track_id, tick)
        )
        ;

        CREATE INDEX IF NOT EXISTS movelet_motion_idx ON movelet
          USING ivfflat (motion vector_cosine_ops);
        """
    )

    await conn.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS video_meta AS
            SELECT video.*, pose_ct, track_ct, shot_ct, poses_per_frame, face_ct, hand_ct
            FROM video
            LEFT JOIN (
                SELECT video.id, COUNT(*) AS face_ct
                FROM video
                INNER JOIN face ON video.id = face.video_id
                GROUP BY video.id
            ) AS f ON video.id = f.id
            LEFT JOIN (
                SELECT video.id, COUNT(*) AS hand_ct
                FROM video
                INNER JOIN hand ON video.id = hand.video_id
                GROUP BY video.id
            ) AS h ON video.id = h.id
            LEFT JOIN (
                SELECT video.id, MAX(frame.shot) as shot_ct
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

        CREATE UNIQUE INDEX IF NOT EXISTS video_meta_id_idx ON video_meta (id);
        """
    )

    await conn.execute(
        """
        CREATE MATERIALIZED VIEW if not exists video_frame_meta as
        SELECT  frame.video_id,
                frame.frame,
                COALESCE(pose_details.track_ct,0) AS track_ct,
                COALESCE(pose_details.face_ct,0) AS face_ct,
                COALESCE(pose_details.hand_ct,0) AS hand_ct,
                COALESCE(pose_details.avg_score,0) AS avg_score,
                CAST(frame.is_shot_boundary AS INT) AS is_shot,
                frame.pose_interest,
                frame.action_interest,
                CASE
                  WHEN frame.total_movement = 'NaN'
                  THEN 0.0
                  ELSE ROUND(frame.total_movement::numeric, 2)
                END AS "movement",
                CASE
                  WHEN frame.total_movement3d = 'NaN'
                  THEN 0.0
                  ELSE ROUND(frame.total_movement3d::numeric, 2)
                END AS "movement3d"
        FROM frame
        LEFT JOIN
            ( SELECT pose.video_id,
                   pose.frame,
                   count(NULLIF(pose.track_id,0)) AS track_ct,
                   count(face.pose_idx) AS face_ct,
                   count(hand.pose_idx) AS hand_ct,
                   ROUND(AVG(pose.score)::numeric, 2) AS avg_score
            FROM pose
            LEFT JOIN face ON
                pose.video_id = face.video_id AND
                pose.frame = face.frame AND
                pose.pose_idx = face.pose_idx
            LEFT JOIN hand ON
                pose.video_id = hand.video_id AND
                pose.frame = hand.frame AND
                pose.pose_idx = hand.pose_idx
            GROUP BY pose.video_id, pose.frame
            ORDER BY pose.frame
            ) AS pose_details
        ON
            frame.video_id = pose_details.video_id AND
            frame.frame = pose_details.frame
        ORDER BY frame.frame
        WITH DATA;

        CREATE INDEX IF NOT EXISTS video_frame_meta_video_id_idx
          ON video_frame_meta (video_id);
        """
    )


# XXX Maybe shouldn't call this file _initialization if this will be here
async def remove_video(self, video_id) -> None:
    async with self._pool.acquire() as conn:
        logging.warning("Removing database entries associated with video")
        await conn.execute("DELETE FROM video WHERE id=$1", video_id)
