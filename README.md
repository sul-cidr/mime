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
VIDEO_SRC_FOLDER=/path/to/source/videos

# DB_HOST=localhost    ## Ignored if using docker-compose.yaml
# DB_PORT=5432         ## Ignored if using docker-compose.yaml
# LOG_LEVEL=INFO       ## Optional: INFO is default, set to DEBUG for additional logging
EOL

docker compose up
```

All being well, the UI should be now available at `http://localhost:8080/`.


## Updating

Update the codebase with `git pull`.  If dependencies are modified, `docker compose up --build` should be used to ensure the images are rebuilt with the new dependencies are available inside the images.


## Accessing remotely

Because all parts of the application are served behind a reverse proxy, everything should be available over a single TCP port.  Something like `ssh -fNTL 3000:localhost:8080 user@mime-server` should be sufficient to expose the UI running on the remote host at http://localhost:3000/ on the local machine.


## Development

The docker configuration is configured with hot-reload, so changes to the source folders on the docker host are immediately reflected in the running containers, so no local dependencies are absolutely required.

Despite this, it is recommended to have `pnpm` and `pipenv` installed on the docker host for the web-ui and the api respectively, and to install dependencies locally, i.e.:

```sh
cd web-ui && pnpm install && cd -
cd api && PIPENV_VENV_IN_PROJECT=1 python -m pipenv install --dev && cd -
```
In addition to making it possible to run parts of the stack independently of the docker configuration, this will make sure dev environments are available to, e.g., VS Cod{ium,e} for linting and static analysis, etc.
