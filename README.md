# MIME: Machine Intelligence for Motion Exegesis

MIME is a collaborative effort between faculty in the Department of Theater and Performance Studies at Stanford University and developers in Research Data Services at the Stanford University Libraries to study recorded theatrical performances through the lens of pose estimation and motion tracking.

This repository contains code for ingesting, indexing and exploring the output of software tools for running pose estimation and related tasks on video files. For further background regarding the technologies used and the research inquiries in which MIME has been applied, please consult these resources:

📄 **Paper**: "Stylistic Analyses of Human Pose in Theatrical Performances: Computational and Historical Frameworks," _Anthology of Computers and the Humanities_ 3, 2025. https://doi.org/10.63744/GxQbSDPPyqvL

📊 **Slides**: "The Director’s Signature: Stylometry of Theater Choreography via Pose and Action Estimation," presented at [Digital Humanities 2025](https://sul-cidr.github.io/mime-dh2025-slides).

🎬 **Video**: "Using Pose and Action Estimation to Analyze Theater Performances," [Stanford HAI Research Seminar](https://www.youtube.com/watch?v=VqenFiXaCDU), January 22, 2025.

## Simple Bring-Up

Make sure docker and the docker-compose plugin are installed (using the docker repos is recommended) and grab the source code:

```sh
git clone https://github.com/sul-cidr/mime.git
cd mime
```

Fill in the `.env` configuration file:

```sh
cat > .env <<EOL
DB_NAME=mime
DB_USER=mime
DB_PASSWORD=yourpasswordhere
# DB_HOST=localhost    ## Ignored if using docker-compose.yaml
# DB_PORT=5432         ## Ignored if using docker-compose.yaml

VIDEO_SRC_FOLDER=/path/to/source/videos

JUPYTER_PASSWORD=secret_password

LOG_LEVEL=INFO       ## Set to DEBUG for additional logging
EOL
```

You will need to modify the value of `VIDEO_SRC_FOLDER` (which will contain both videos and other input data files) to fit your local setup. Most other values can be left as above, though you also may wish to set `DB_PASSWORD` to an obscure string, such as can be obtained on some systems by running
`LC_ALL=C tr -cd 'a-zA-Z0-9' < /dev/urandom | fold -w24 | head -n 1`.

Then, to build and/or refresh the local containers and start MIME:

```sh
docker compose up
```

All being well, the UI should be now available at `http://localhost:8080/`.

### Jupyter

If using the docker configuration, a Jupyter Notebook server will be available at `http://localhost:8080/jupyter/` (linked from the UI header). At the present time it is necessary to grab the authentication token from the api container logs each time the container is rebuilt. If launching the API server from a `venv` on the host, the notebook-specific requirements from [`api/notebooks/notebook_requirements.txt`](api/notebooks/notebook_requirements.txt) must be installed in the `venv` (e.g., something like `pipenv run pip install -r notebooks/notebook_requirements.txt`).

## just

A [`justfile`](./justfile) is provided to simplify some commands -- if you have [`just`](https://github.com/casey/just) installed, execute `just` from the repository working folder to see a list of available commands.

## Updating

Update the codebase with `git pull`. If dependencies are modified, `docker compose build` (or `just build`) should be used to ensure the images are rebuilt with the new dependencies are available inside the images.

## Accessing remotely

When using the docker bring-up, all parts of the application are served behind a reverse proxy so everything is available over a single TCP port. Something like `ssh -fNTL 3000:localhost:8080 user@mime-server` should be sufficient to expose the UI running on the remote host at http://localhost:3000/ on the local machine.

## Development

The docker configuration is configured with hot-reload, so changes to the source folders on the docker host are immediately reflected in the running containers and no local dependencies are required for development.

Despite this, it is recommended to have `pnpm` and `pipenv` installed on the docker host for the web-ui and the api respectively, and to install dependencies locally, i.e.:

```sh
cd web-ui && pnpm install && cd -
cd api && PIPENV_VENV_IN_PROJECT=1 python -m pipenv install --dev && cd -
```

In addition to making it possible to run parts of the stack independently of the docker configuration, this will make sure dev environments are available to, e.g., VS Cod{ium,e} for linting and static analysis, etc.

## Ingesting videos for analysis

The processing steps are  subject to change as analytical methods are added or modified, but the full sequence for adding a performance video to the platform as of October 2025 is as described below. The provided file paths are all relative to the folder on the host system set by `VIDEO_SRC_FOLDER=` in the `.env` file. Note that the steps assume an output .pkl file from running pose estimation on the video file is already present in the same folder as the video; the other video analysis steps now can be done via the commands below.

Steps marked with an asterisk `*` may be optional if a viable output file is present from a previous run of the step.

1. `just add-video-4dh Video_File_Name.ext [pose_sample_rate]` - Creates a DB entry for the video, then locates the PHALP/4D-Humans pose estimation output file as `Video_File_Name.ext.phalp.pkl` and imports the data into the DB. If `pose_sample_rate` is specified, the import process will sample this many frames per second and only import pose data for those frames.
1. `just detect-shots Video_File_Name.ext` - Runs shot detection on each frame of the video file and writes the output to `Video_File_Name.ext.shots.TransNetV2.pkl`.\*
1. `just add-shots Video_File_Name.ext` - Looks for a shot detection output file named `Video_File_Name.ext.shots.TransNetV2.pkl` generated for the video via the `api/detect_shots.py` script in the repo (see previous step) and imports the data into the DB.
1. `just do-poem-embeddings Video_File_Name.ext` - Exports the normalized COCO 13-keypoint poses for a video into a CSV file (at `api/poem_files/Video_File_Name.ext.csv`) to be used as input when creating view-invariant pose embeddings via the Pr-VIPE model from the [POEM project](https://sites.google.com/view/pr-vipe), then runs the POEM view-invariant pose embedding generation software on the CSV, producing an output CSV file that is then loaded into the DB to create a view-invariant search index on the poses.
1. `just add-motion Video_File_Name.ext [tick_interval]` - Segments pose tracks into "movelets" consisting of the average position of consecutive poses that occur within one `tick_interval` of each other, then computes the degree of motion between adjacent movelets. The `tick_interval` value defaults to 1/6s, but if a `pose_sample_rate` was provided above, it may need to be set to a longer duration that is an integer multiple of the `pose_sample_rate`.
1. `just load-actions Video_File_Name.ext.lart.pkl` - Loads externally generated action recognition output data for a given video from a file named `Video_File_name.ext.lart.pkl`.\*
1. `just calculate-pose-interest Video_File_Name.ext` - Compares each pose to the global average pose for the video, computes the degree to which the poses in each frame deviate from the average, and represents the frame's "interest" level as the maximum of these values.
1. `just calculate-action-interest Video_File_Name.ext` - If action recognition data has been loaded previously for a video, compares each pose's action vector to the global average for the video, computes the degree to which the poses in each frame deviate from the average, and represents the frame's "interest" level as the maximum of these values.\*
1. `just detect-faces Video_File_Name.ext` - Runs face detection on each frame of the video file and writes the output to `Video_File_Name.faces.ArcFace.jsonl`. Note that this can take a very long time to run (as long as the initial offline pose estimation task). You may prefer to run the `api/detect_faces.py` script separately as a batch job.\*
1. `just match-faces Video_File_Name.ext` - Looks for a face detection output file named `Video_File_Name.ext.faces.ArcFace.jsonl` generated for the video via the `api/detect_faces.py` script in the repo, matches detected poses with detected faces and adds the information to the DB.
1. `just match-hands Video_File_Name.ext` - Looks for a hand detection output file named `Video_File_Name.ext.hands.WiLoR.jsonl` generated for the video via the `api/detect_hands.py` script in the repo, matches detected poses with detected hands and adds the information to the DB.
1. `**OPTION 1**: just detect-labeled-faces Video_File_Name.ext` - Assumes you have placed headshot image files in `api/face_images/Video_File_Name.ext`, one for each face you want to search for in the video, named by the associated role or actor, e.g., "Julius_Caesar.png". This runs face detection on the headshots and produces a .json summary of their features in the same folder.
1. `**OPTION 1**: just match-labeled-faces Video_File_Name.ext` - If face detection output has been loaded into the DB via `just match-faces` and `just detect-faces`, and `just detect-labeled-faces` also has been run, this runs a similarity analysis between detected faces in the video and the target face features corresponding to the images in `api/face_images/Video_File_Name.ext` and saves the results to the DB to create a timeline of occurrences of the target faces in the video.
1. `**OPTION 2**: just cluster-faces Video_File_Name.ext [NUMBER_OF_PERSONS]` - If face detection output has been loaded into the DB via `just match-faces` and `just detect-faces`, performs K-means clustering on the face features and saves the results to the DB to create a timeline of every (suspected) occurrence of a person in the video. NUMBER_OF_PERSONS is approximately the total number of individual faces expected to be in the video (which may or may not correspond to the size of the cast).
1. `just cluster-poses Video_File_Name.ext [NUMBER_OF_POSES]` - Performs K-means clustering on representative poses in tracked movelets, assuming the specified NUMBER_OF_POSES pose archetypes, and saves the results to the DB to enable an interactive timeline display of the pose cluster membership.
1. `just cluster-plot-poses Video_File_Name.ext [NUMBER_OF_POSES]` - Generates data for the PosePlot (née PixPlot) pose set navigator visualization accessible from the "Explorer" tab in the MIME app. Note that the process of creating cutout images for all representative poses within a video can take several hours.
