FROM python:3.11-slim

RUN pip install --no-cache-dir kubernetes pyyaml

WORKDIR /app
COPY deploy.py            .
COPY manifests/           manifests/

ENTRYPOINT ["python", "deploy.py"]