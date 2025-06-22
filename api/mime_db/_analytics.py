import io

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.spatial import distance_matrix
from scipy.stats import kurtosis, kurtosistest, skew, skewtest

font = {"family": "normal", "weight": "normal", "size": 8}

plt.rc("font", **font)


# Helper/lib functions duplicated from pose_information_retrieval.ipynb
# Consider DRYing up...
def get_distribution_stats(distrib, plot=False):
    if len(distrib) == 0:
        return {
            "count": 0,
            "mean": 0,
            "median": 0,
            "stdev": 0,
            "skewness": 0,
            "kurtosis": 0,
        }

    if skewtest(distrib).pvalue < 0.05:
        skewness = skew(distrib)
    else:
        skewness = 0

    if kurtosistest(distrib).pvalue < 0.05:
        kurtosis_value = kurtosis(distrib)
    else:
        kurtosis_value = 0

    if plot:
        plt.hist(distrib, bins="auto")  # arguments are passed to np.histogram
        plt.show()

    return {
        "count": len(distrib),
        "mean": round(np.mean(distrib), 4),
        "median": round(np.median(distrib), 4),
        "stdev": round(np.std(distrib), 4),
        "skewness": round(skewness, 4),
        "kurtosis": round(kurtosis_value, 4),
    }


def project_pose(keypoints3d, camera):
    kp_array = np.array(np.split(keypoints3d, 13))
    kp_camera = np.array(camera)
    return kp_array + kp_camera.T


def get_projected_pose_centroid(keypoints3d, camera):
    proj_centroid = np.mean(project_pose(keypoints3d, camera), axis=0)
    proj_centroid[2] = proj_centroid[2] / 200  # Z axis is exaggerated in PHALP output
    return proj_centroid


def get_histogram_image(viz_data):
    fig = plt.figure(figsize=(3, 2), dpi=100)
    fig.add_subplot(111)

    plt.hist(viz_data, bins="auto")  # arguments are passed to np.histogram

    fig.canvas.draw()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)

    img_array = np.array(Image.open(buf))
    buf.close()

    return img_array


def get_video_spacing(pose_frame_data):
    distances = []

    current_frame = 0
    current_frame_centroids = []
    for r, rec in enumerate(pose_frame_data):
        frame = rec.get("frame")
        camera = rec.get("camera")
        keypoints3d = rec.get("keypoints3d")
        if current_frame > 0 and (
            frame != current_frame or r == len(pose_frame_data) - 1
        ):
            if r == len(pose_frame_data) - 1:  # For the last pose in the last frame
                current_frame_centroids.append(
                    get_projected_pose_centroid(keypoints3d, camera)
                )
            # Compute distances for the frame
            dist_matrix = distance_matrix(
                current_frame_centroids, current_frame_centroids
            )
            upper_diagonal = list(dist_matrix[np.triu_indices(len(dist_matrix), k=1)])
            distances.extend(upper_diagonal)
            current_frame = frame
            current_frame_centroids = []

        if current_frame == 0 and frame > 0:
            current_frame = frame

        current_frame_centroids.append(get_projected_pose_centroid(keypoints3d, camera))
    return distances


async def analyze_video_motion(self, video_ids: tuple[str], is_3d: bool) -> list:
    in_clause = ",".join(f"'{video_id}'" for video_id in video_ids)
    if is_3d:
        query_field = "movement3d"
    else:
        query_field = "movement"
    return await self._pool.fetch(
        f"""
        WITH mean_median_stdev AS (
            SELECT
                video_id,
                ROUND(AVG({query_field}::NUMERIC), 4) AS mean,
                ROUND(STDDEV({query_field}::NUMERIC), 4) AS stdev,
                ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {query_field})::NUMERIC, 4) AS median
            FROM movelet
            WHERE video_id IN({in_clause}) AND {query_field} > 0
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


async def viz_video_motion(self, video_id: str, is_3d: bool) -> np.ndarray:
    if is_3d:
        query_field = "movement3d"
    else:
        query_field = "movement"

    vid_data = await self._pool.fetch(
        f"""
        SELECT {query_field}
        FROM movelet
        WHERE video_id='{video_id}' AND {query_field} > 0
        ;
        """
    )

    viz_data = [rec[query_field] for rec in vid_data]

    return get_histogram_image(viz_data)


async def analyze_video_spacing(self, video_ids: tuple[str]) -> list:
    distances_by_video = {}
    for video_id in video_ids:
        pose_frame_data = await self._pool.fetch(
            f"""
            SELECT frame, keypoints3d, camera FROM pose
            WHERE video_id='{video_id}'
            GROUP BY frame, keypoints3d, camera
            ORDER BY frame
            ;
            """
        )
        distances_by_video[video_id] = get_video_spacing(pose_frame_data)

    output_stats = []
    for video_id in distances_by_video:
        video_stats = {"video_id": video_id} | get_distribution_stats(
            distances_by_video[video_id]
        )
        output_stats.append(video_stats)

    return output_stats


async def viz_video_spacing(self, video_id: str) -> np.ndarray:
    pose_frame_data = await self._pool.fetch(
        f"""
        SELECT frame, keypoints3d, camera FROM pose
        WHERE video_id='{video_id}'
        GROUP BY frame, keypoints3d, camera
        ORDER BY frame
        ;
        """
    )
    distances = get_video_spacing(pose_frame_data)

    return get_histogram_image(distances)


# async def get_video_by_id(self, video_id: UUID) -> asyncpg.Record:
#     return await self._pool.fetchrow("SELECT * FROM video WHERE id = $1;", video_id)
