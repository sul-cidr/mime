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
