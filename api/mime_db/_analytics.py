import io
import json
import os

import matplotlib as mpl
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.spatial import distance_matrix
from scipy.spatial.distance import cosine, euclidean
from scipy.stats import kurtosis, kurtosistest, skew, skewtest

from lib.pose_utils import get_poem_embedding

font = {"weight": "normal", "size": 8}

plt.rc("font", **font)

MIN_MOVELET_DURATION = 0.1

fingerprints = {}
if os.path.exists("archetypes/archetype_fingerprints.json"):
    with open("archetypes/archetype_fingerprints.json", "r") as fingerprints_file:
        fingerprints = json.load(fingerprints_file)

# Helper/lib functions duplicated from pose_information_retrieval.ipynb
# Consider DRYing up...
def get_distribution_stats(distrib):
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

    plt.hist(viz_data, bins=300)  # arguments are passed to np.histogram

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


def get_sidereal_motion(track_movelet_data, video_fps):
    movements = []
    for movelet in track_movelet_data:
        duration = (
            movelet.get("end_frame") / video_fps - movelet.get("start_frame") / video_fps
        )
        if duration < MIN_MOVELET_DURATION:
            continue
        start_centroid = get_projected_pose_centroid(
            movelet.get("start_pose3d"), movelet.get("start_camera")
        )
        end_centroid = get_projected_pose_centroid(
            movelet.get("end_pose3d"), movelet.get("end_camera")
        )
        distance = euclidean(start_centroid, end_centroid)
        if distance == 0:
            continue
        movements.append(distance / duration)
    return movements


async def analyze_video_sidereal(self, video_ids: tuple[str]) -> list:
    movements_by_video = {}
    for video_id in video_ids:
        video_data = await self.get_video_by_id(video_id)
        video_fps = video_data["fps"]

        movements_by_video[video_id] = []

        track_movelet_data = await self._pool.fetch(
            f"""
            WITH movelet_start_pose AS (
                SELECT movelet.track_id, start_frame, end_frame, movelet.pose_idx, keypoints3d, camera
                FROM movelet LEFT JOIN pose ON
                    movelet.video_id = pose.video_id
                    AND movelet.start_frame = pose.frame
                    AND movelet.track_id = pose.track_id
                WHERE movelet.video_id='{video_id}'
            ), movelet_end_pose AS (
                SELECT movelet.track_id, start_frame, end_frame, movelet.pose_idx, keypoints3d, camera
                FROM movelet LEFT JOIN pose ON
                    movelet.video_id = pose.video_id
                    AND movelet.end_frame = pose.frame
                    AND movelet.track_id = pose.track_id
                WHERE movelet.video_id='{video_id}'
            )
            SELECT
                movelet_start_pose.track_id,
                movelet_start_pose.start_frame,
                movelet_end_pose.end_frame,
                movelet_start_pose.keypoints3d AS start_pose3d,
                movelet_start_pose.camera AS start_camera,
                movelet_end_pose.keypoints3d AS end_pose3d,
                movelet_end_pose.camera AS end_camera
            FROM movelet_start_pose, movelet_end_pose
            WHERE movelet_start_pose.track_id = movelet_end_pose.track_id
                AND movelet_start_pose.start_frame = movelet_end_pose.start_frame
                AND movelet_start_pose.end_frame = movelet_end_pose.end_frame
                AND movelet_start_pose.start_frame < movelet_end_pose.end_frame
            ;
            """
        )

        movements_by_video[video_id] = get_sidereal_motion(track_movelet_data, video_fps)

    output_stats = []
    for video_id in movements_by_video:
        video_stats = {"video_id": video_id} | get_distribution_stats(
            movements_by_video[video_id]
        )
        output_stats.append(video_stats)

    return output_stats


async def viz_video_sidereal(self, video_id: str) -> np.ndarray:
    video_data = await self.get_video_by_id(video_id)
    video_fps = video_data["fps"]

    track_movelet_data = await self._pool.fetch(
        f"""
        WITH movelet_start_pose AS (
            SELECT movelet.track_id, start_frame, end_frame, movelet.pose_idx, keypoints3d, camera
            FROM movelet LEFT JOIN pose ON
                movelet.video_id = pose.video_id
                AND movelet.start_frame = pose.frame
                AND movelet.track_id = pose.track_id
            WHERE movelet.video_id='{video_id}'
        ), movelet_end_pose AS (
            SELECT movelet.track_id, start_frame, end_frame, movelet.pose_idx, keypoints3d, camera
            FROM movelet LEFT JOIN pose ON
                movelet.video_id = pose.video_id
                AND movelet.end_frame = pose.frame
                AND movelet.track_id = pose.track_id
            WHERE movelet.video_id='{video_id}'
        )
        SELECT
            movelet_start_pose.track_id,
            movelet_start_pose.start_frame,
            movelet_end_pose.end_frame,
            movelet_start_pose.keypoints3d AS start_pose3d,
            movelet_start_pose.camera AS start_camera,
            movelet_end_pose.keypoints3d AS end_pose3d,
            movelet_end_pose.camera AS end_camera
        FROM movelet_start_pose, movelet_end_pose
        WHERE movelet_start_pose.track_id = movelet_end_pose.track_id
            AND movelet_start_pose.start_frame = movelet_end_pose.start_frame
            AND movelet_start_pose.end_frame = movelet_end_pose.end_frame
            AND movelet_start_pose.start_frame < movelet_end_pose.end_frame
        ;
        """
    )

    movements = get_sidereal_motion(track_movelet_data, video_fps)

    return get_histogram_image(movements)


async def generate_profile(self, poses_or_hands: str, metric: str, video_id: str) -> np.ndarray:

    if poses_or_hands == "poses":
        video_poses_or_hands = await self.get_pose_data_from_video(video_id)
        with open("archetypes/pose_archetypes.json", "r") as poses_file:
            archetypes = json.load(poses_file)
    else:
        video_poses_or_hands = await self.get_hand_data_from_video(video_id)
        with open("archetypes/hand_archetypes.json", "r") as hands_file:
            archetypes = json.load(hands_file)
    
    descriptions = [arch["description"] for arch in archetypes]

    # Rudimentary support for supplying pre-calculated fingerprints.
    # Falls back to computing the fingerprints on the fly if data is missing.
    try:
        archetype_similarities = fingerprints[poses_or_hands][video_id][metric]
        print("using cached fingerprints")
    except Exception as e:
        print("computing fingerprints")
        archetype_similarities = []
        for archetype in archetypes: # [:10]
            sims = []
            archetype_vector = archetype[metric]
            for pose_or_hand in video_poses_or_hands:
                sims.append(1 - cosine(archetype_vector, pose_or_hand[metric]))
            archetype_similarities.append(np.mean(sims))

    def offset_image(x, y, arch, bar_is_too_short, ax):
        img = plt.imread(f"archetypes/{poses_or_hands}/{arch['image_filename']}")
        im = OffsetImage(img, zoom=.09, cmap=mpl.colormaps['gray'])
        im.image.axes = ax
        x_offset = .2
        if bar_is_too_short:
            x = 0
        ab = AnnotationBbox(im, (x, y), xybox=(x_offset, 0), frameon=False,
                            xycoords='data', boxcoords="offset points", pad=0)
        ax.set_facecolor('#FFFFFF')
        ax.add_artist(ab)

    fig = plt.figure(figsize=(10,12), dpi=100)
    height = .5
    fingerprint_data = list(reversed(archetype_similarities))
    plt.barh(list(reversed(descriptions)), fingerprint_data, height=height, align='center', alpha=0.8, color="#663399")
    ax = plt.gca()
    ax.tick_params(axis="y", labelrotation=40)

    max_value = max(fingerprint_data)

    for a, arch in enumerate(list(reversed(archetypes))):
        img = plt.imread(f"archetypes/{poses_or_hands}/{arch['image_filename']}")
        value = fingerprint_data[a]
        offset_image(value, a, arch, bar_is_too_short=value < max_value / 10, ax=plt.gca())
        
    plt.subplots_adjust(left=0.15)

    plt.xlim(0, 1.10)
    plt.ylim(-0.5, len(descriptions) - 0.5)
    plt.tight_layout()

    fig.canvas.draw()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)

    img_array = np.array(Image.open(buf))
    buf.close()

    return img_array