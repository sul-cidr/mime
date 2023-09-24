# mime

## Simple Bring-Up

Make sure docker and the docker-compose plugin are installed (using the docker repos is recommended) first.

```sh
git clone https://github.com/sul-cidr/mime.git

cd mime

cat > .env <<EOL
DB_NAME=mime
DB_USER=mime
DB_PASSWORD=$(LC_ALL=C tr -cd 'a-zA-Z0-9' < /dev/urandom | fold -w24 | head -n 1)
# DB_HOST=localhost    ## Ignored if using docker-compose.yaml
# DB_PORT=5432         ## Ignored if using docker-compose.yaml

VIDEO_SRC_FOLDER=/path/to/source/videos

JUPYTER_PASSWORD=secret_password

LOG_LEVEL=INFO       ## Set to DEBUG for additional logging
EOL

docker compose up
```

(`VIDEO_SRC_FOLDER` is the only value that must be supplied -- it is suggested that other values be left as above.)

All being well, the UI should be now available at `http://localhost:8080/`.

### Jupyter

If using the docker configuration, a Jupyter Notebook server will be available at `http://localhost:8080/jupyter/` (linked from the UI header) At the present time it is necessary to grab the authentication token from the api container logs each time the container is rebuilt. If launching the API server from a `venv` on the host, the notebook-specific requirements from [`api/notebooks/notebook_requirements.txt`](api/notebooks/notebook_requirements.txt) must be installed in the `venv` (e.g. something like `pipenv run pip install -r notebooks/notebook_requirements.txt`).

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

The processing steps are highly subject to change as analytical methods are added or modified, but as of late September 2023, the full sequence for adding a performance video to the platform is as described below. The provided file paths are all relative to the folder on the host system set by `VIDEO_SRC_FOLDER=` in the `.env` file.

1. `just add-video Video_File_Name.ext` - Creates a DB entry for the video, then locates the pose estimation output file as `Video_File_Name.ext.openpifpaf.json` and imports the data into the DB.
2. `just add-tracks Video_File_Name.ext` - Applies object tracking to the pose position data in the DB to join adjacent poses by the same figure into "tracks" that are saved in the DB.
3. `just add-motion Video_File_Name.ext` - Segments pose tracks into "movelets" consisting of the average position of consecutive poses that occur within 1/6 of a second of each other, then computes the degree of motion between adjacent movelets.
4. `just match-faces Video_File_Name.ext Video_Faces_File_Name.ext` - [optional] If face detection output has been generated for the video via the `detect_faces_offline.py` script in the repo, this matches detected poses with detected faces and adds the information to the DB.
5. `just plot-poses Video_File_Name.ext` - Generates data for the pose clustering visualization.
