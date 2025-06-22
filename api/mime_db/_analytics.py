async def analyze_video_motion(self, video_ids: tuple[str]) -> list:
    in_clause = ",".join(f"'{video_id}'" for video_id in video_ids)
    return await self._pool.fetch(
        f"""
        WITH mean_median_stdev AS (
            SELECT
                video_id,
                ROUND(AVG(total_movement3d::NUMERIC), 4) AS mean,
                ROUND(STDDEV(total_movement3d::NUMERIC), 4) AS stdev,
                ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_movement3d)::NUMERIC, 4) AS median
            FROM frame
            WHERE video_id IN({in_clause}) AND total_movement3d > 0
            GROUP BY video_id
        )
        SELECT
            video_id,
            mean,
            median,
            stdev,
            ROUND(3.0 * (mean - median)::NUMERIC / stdev, 4) AS skewness
        FROM mean_median_stdev
        ;
        """,
    )


# async def get_video_by_id(self, video_id: UUID) -> asyncpg.Record:
#     return await self._pool.fetchrow("SELECT * FROM video WHERE id = $1;", video_id)
