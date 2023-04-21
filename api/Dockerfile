# Some of the stuff we need doesn't work well on Alpine
FROM python:3.10-slim

# Container is used with live-reload so we don't want .pyc stored on bind-mounted host filesystem
ENV PYTHONPYCACHEPREFIX=/tmp

WORKDIR /app
EXPOSE 5000
COPY . .
RUN pip install pipenv && pipenv install --dev --deploy --system
ENTRYPOINT ["python", "/app/server.py"]
