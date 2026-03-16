# Some of the stuff we need doesn't work well on Alpine
FROM python:3.10-slim

WORKDIR /app
EXPOSE 5000

# Container is used with live-reload so we don't want .pyc stored on bind-mounted host filesystem
ENV PYTHONPYCACHEPREFIX=/tmp
# Makes local modules easy to use from Jupyter
ENV PYTHONPATH=$PYTHONPATH:/app
# Allow websocket connections from the main app host
ENV BOKEH_ALLOW_WS_ORIGIN=localhost:8080

# Install dependencies from apt repos
# * build-essential takes care of what is needed to build the lap binaries
# * installing python3-opencv is the easiest way to ensure we have
#    the needed libraries that will support pip-installed cv2
RUN apt-get update -qq \
  && apt-get install -y supervisor build-essential python3-opencv ffmpeg pkg-config libhdf5-dev \
  && rm -rf /var/lib/apt/lists/*

# Configure supervisord
RUN <<EOF cat >> /stop-supervisor.sh
#!/usr/bin/env bash
set -Eeo pipefail
while read -r; do
  echo -e "\e[31m Service was stopped or one of it's services crashed,
            see the logs above for more details. \e[0m" >&2
  kill -SIGTERM "$(cat supervisord.pid)"
done < /dev/stdin
EOF
RUN chmod 755 /stop-supervisor.sh

RUN <<EOF cat >> /etc/supervisor/conf.d/supervisord.conf
[supervisord]
nodaemon=true
user=root
logfile=/var/log/supervisor/supervisord.log 
pidfile=/var/run/supervisord.pid
childlogdir=/var/log/supervisor

[program:api-server]
directory=/app/
command=python /app/server.py
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0

[program:notebook-server]
directory=/app/
command=jupyter notebook --allow-root --no-browser --NotebookApp.base_url=/jupyter --NotebookApp.allow_origin='*' --port=8888 --ip=0.0.0.0
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0

[eventlistener:processes]
directory=/app/
command=/stop-supervisor.sh
events=PROCESS_STATE_STOPPED,PROCESS_STATE_EXITED,PROCESS_STATE_FATAL
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
EOF

# Copy Pipfile and Pipfile.lock first for caching
COPY Pipfile /app/

# Install pipenv and dependencies from the lockfile
RUN python -m pip install --upgrade pip \
  && python -m pip install pipenv

# Generate lockfile if missing, then install dependencies
RUN if [-f Pipfile.lock]; then pipenv lock; fi

#Install dependencies to system python
RUN pipenv install --dev --system --deploy || true

#Installing open cv
RUN pip install --no-cache-dir opencv-python

#Installing uvicorn
RUN pip install uvicorn

#Installing dotenv
RUN pip install dotenv

#Installing fastapi
RUN pip install fastapi

#Installing fastapi-utils
RUN pip install fastapi-utils

#Installing typing_inspect
RUN pip install typing_inspect

#Installing asyncpg
RUN pip install asyncpg
#Installing pgvector
RUN pip install pgvector

#Installing joblib
RUN pip install joblib

# Copy application code
COPY . .

# Install application dependencies
RUN pip install pipenv
RUN pipenv lock && pipenv --clear && pipenv --rm
RUN pipenv install --dev --deploy --system

# lap is now  a dependency for the api container, not just the notebook
RUN pip install --no-cache-dir lap

# Install jupyter and notebook-only dependencies
# (not added to Pipfile as it doesn't make sense to include it as part of the 
#  API server -- if it's desired outside of this docker config then venv
#  kernels must be compiled on the host etc.)
# Note: do this after installing application dependencies so that numpy is
#       available as a build dependency for lap
RUN pip install --no-cache-dir --upgrade -r /app/notebooks/notebook_requirements.txt

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
