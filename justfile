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
