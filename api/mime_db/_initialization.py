import logging


async def initialize_db(conn, drop=False) -> None:
    if drop:
        logging.warn("Dropping database tables...")
        await conn.execute("DROP TABLE IF EXISTS video CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS pose CASCADE;")

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
            PRIMARY KEY(video_id, frame, pose_idx)
        )
        ;
        """
    )
