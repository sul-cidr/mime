set positional-arguments

[private]
default:
  @just --list

# Start the application
@up:
  docker compose up

# (Re)build all containers
@build:
  docker compose build

# Provide paths relative to $VIDEO_SRC_FOLDER
@add-video path:
  docker compose exec api sh -c "/app/load_video.py --video-path \"\$VIDEO_SRC_FOLDER/$1\""

@add-tracks path:
  docker compose exec api sh -c "/app/track_video.py --video-path \"\$VIDEO_SRC_FOLDER/$1\""

@add-motion path:
  docker compose exec api sh -c "/app/track_video_motion.py --video-path \"\$VIDEO_SRC_FOLDER/$1\""

@add-faces path:
  docker compose exec api sh -c "/app/detect_pose_faces.py --video-path \"\$VIDEO_SRC_FOLDER/$1\""

@load-faces path:
  docker compose exec api sh -c "/app/load_face_data.py --json-path \"\$VIDEO_SRC_FOLDER/$1\""

#@match-faces :
#  docker compose exec api sh -c "/app/match_faces_to_poses.py --video-name \"\$VIDEO_SRC_FOLDER/$1\""

@match-faces video_path faces_path:
  docker compose exec api sh -c "/app/match_offline_faces_to_poses.py --video-name \"\$VIDEO_SRC_FOLDER/$1\" --faces-file \"\$VIDEO_SRC_FOLDER/$2\""

@cluster-faces path:
  docker compose exec api sh -c "/app/cluster_pose_faces.py --video-path \"\$VIDEO_SRC_FOLDER/$1\""
