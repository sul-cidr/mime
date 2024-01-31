set positional-arguments
set dotenv-load

# [private]
default:
  @just --list

# Start the application
@up:
  docker compose up

# (Re)build all containers
@build:
  docker compose build

# Lint Python files with ruff
@lint:
  docker compose exec api ruff check .

# Lint Python files with ruff, and fix where possible
@lint-fix:
  docker compose exec api ruff check --fix .

# Build a production bundle of the front-end code for faster UI
@build-prod-ui:
  docker compose exec web-ui sh -c 'pnpm $MODULES_DIR/.bin/astro build'

# Drop and rebuild the database (obviously use with caution!)
@drop-and-rebuild-db:
  docker compose exec api python -c 'import asyncio;from mime_db import MimeDb;asyncio.run(MimeDb.create(drop=True))'

# Refresh PostgreSQL materialized views
@refresh-db-views:
  docker compose exec db sh -c 'psql -U mime -c "REFRESH MATERIALIZED VIEW CONCURRENTLY video_meta; REFRESH MATERIALIZED VIEW video_frame_meta;"'

# Video file and pose detection output file are in $VIDEO_SRC_FOLDER; the latter is [VIDEO_FILE_NAME].openpifpaf.json
@add-video path: && refresh-db-views
  docker compose exec api sh -c "LOG_LEVEL=$LOG_LEVEL /app/load_video.py --video-path \"\$VIDEO_SRC_FOLDER/$1\""

# Remove a video by name and all associated records in other tables linked via its UUID
@remove-video path: && refresh-db-views
  docker compose exec api sh -c "LOG_LEVEL=$LOG_LEVEL /app/remove_video.py --video-path \"\$VIDEO_SRC_FOLDER/$1\""

@add-video-4dh path: && refresh-db-views
  docker compose exec api sh -c "LOG_LEVEL=$LOG_LEVEL /app/load_video_4dh.py --video-path \"\$VIDEO_SRC_FOLDER/$1\""

# Video file is in $VIDEO_SRC_FOLDER; detected shots file will be [VIDEO_FILE_NAME].shots.TransNetV2.pkl
@detect-shots path:
  docker compose exec api sh -c "LOG_LEVEL=$LOG_LEVEL /app/detect_shots_offline.py --video-path \"\$VIDEO_SRC_FOLDER/$1\""

# Load detected shot boundary data; input file is in $VIDEO_SRC_FOLDER with extension .shots.TransNetV2.pkl
@add-shots path: && refresh-db-views
  docker compose exec api sh -c "LOG_LEVEL=$LOG_LEVEL /app/load_shot_boundaries.py --video-path \"\$VIDEO_SRC_FOLDER/$1\""

# Video file is in $VIDEO_SRC_FOLDER; detected faces file will be [VIDEO_FILE_NAME].faces.ArcFace.jsonl
@detect-faces path:
  docker compose exec api sh -c "LOG_LEVEL=$LOG_LEVEL /app/detect_faces_offline.py --video-path \"\$VIDEO_SRC_FOLDER/$1\""

# Provide path to video file relative to $VIDEO_SRC_FOLDER; DO NOT RUN with 4DH data
@add-tracks path: && refresh-db-views
  docker compose exec api sh -c "LOG_LEVEL=$LOG_LEVEL /app/track_video.py --video-path \"\$VIDEO_SRC_FOLDER/$1\""

# Provide path to video file relative to $VIDEO_SRC_FOLDER
@add-motion path: && refresh-db-views
  docker compose exec api sh -c "LOG_LEVEL=$LOG_LEVEL /app/track_video_motion.py --video-path \"\$VIDEO_SRC_FOLDER/$1\""

# @add-faces path:
#   docker compose exec api sh -c "LOG_LEVEL=$LOG_LEVEL /app/detect_pose_faces.py --video-path \"\$VIDEO_SRC_FOLDER/$1\""

# @load-faces path:
#   docker compose exec api sh -c "LOG_LEVEL=$LOG_LEVEL /app/load_face_data.py --json-path \"\$VIDEO_SRC_FOLDER/$1\""

# @match-faces :
#   docker compose exec api sh -c "LOG_LEVEL=$LOG_LEVEL /app/match_faces_to_poses.py --video-name \"\$VIDEO_SRC_FOLDER/$1\""

# Load detected faces data; input file is in $VIDEO_SRC_FOLDER with extension .faces.ArcFace.jsonl
@match-faces video_path: && refresh-db-views
  docker compose exec api sh -c "LOG_LEVEL=$LOG_LEVEL /app/match_offline_faces_to_poses.py --video-name \"\$VIDEO_SRC_FOLDER/$1\""

# @cluster-faces path:
#   docker compose exec api sh -c "LOG_LEVEL=$LOG_LEVEL /app/cluster_pose_faces.py --video-path \"\$VIDEO_SRC_FOLDER/$1\""

# Provide path to video file relative to $VIDEO_SRC_FOLDER
@cluster-faces path n_clusters: && refresh-db-views
  docker compose exec api sh -c "LOG_LEVEL=$LOG_LEVEL /app/cluster_video_faces.py --video-name \"\$VIDEO_SRC_FOLDER/$1\" --n_clusters $2"

# Provide path to video file relative to $VIDEO_SRC_FOLDER
@cluster-poses path n_clusters: && refresh-db-views
  docker compose exec api sh -c "LOG_LEVEL=$LOG_LEVEL /app/cluster_video_poses.py --video-name \"\$VIDEO_SRC_FOLDER/$1\" --n_clusters $2"

# Provide path to video file relative to $VIDEO_SRC_FOLDER
@plot-poses path:
  docker compose exec api sh -c "LOG_LEVEL=$LOG_LEVEL /app/poseplot_prep.py --video-path \"\$VIDEO_SRC_FOLDER/$1\""
  docker compose exec web-extras sh -c "pixplot --images \"input/$1/pose_images/*.jpg\" --vectors input/$1/pose_features --metadata input/$1/$1.csv"
  docker compose exec web-extras sh -c "/bin/mkdir -p /app/poseplot/$1"
  docker compose exec web-extras sh -c "/bin/mv /app/output/* /app/poseplot/$1/."


# Print a mapping of UUIDs to video file names
print-videos:
  #!/usr/bin/env bash
  docker exec -i mime-api python - <<< '
  import asyncio
  from mime_db import MimeDb
  async def _():
      db = await MimeDb.create()
      print("\n".join(f"""{v.get("id")} {v.get("video_name")}""" for v in await db.get_available_videos()))
  asyncio.run(_())
  '

# Probably don't use this
generate-image-cache-naive:
  # just print-videos | while read id name; do docker exec -i mime-api bash -c 'mkdir -p "$CACHE_FOLDER"/'$id'/frames; ffmpeg -i "$VIDEO_SRC_FOLDER"/"'$name'" -f image2 "$CACHE_FOLDER"/'$id'/frames/%d.jpeg'; done;
  just print-videos | while read id name; do echo "sudo mkdir -p "$CACHE_FOLDER"/$id/frames; sudo ffmpeg -i "$VIDEO_SRC_FOLDER"/"$name" -f image2 "$CACHE_FOLDER"/"$id"/frames/%d.jpeg"; done;

# Write hidden files into cache folders to facilitate easier identification
write-cache-folder-labels:
  just print-videos | docker exec -i mime-api bash -c 'while read id name; do touch "$CACHE_FOLDER/$id/.$name"; done;'

# Delete cached pose JSON
clear-cached-pose-json:
  docker exec -i mime-api bash -c "find \$CACHE_FOLDER/ -maxdepth 2 -type f -iname '*.json' -delete"
