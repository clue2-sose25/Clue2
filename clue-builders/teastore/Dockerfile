FROM python:3.13.3-alpine

# Set working directory
WORKDIR /app

# Install system dependencies, Docker CLI, buildx plugin, Git, dos2unix, and Maven
RUN apk update \
    && apk add --no-cache \
       docker-cli \
       docker-cli-buildx \
       git \
       dos2unix \
       openjdk17 \
       maven \
    && rm -rf /var/cache/apk/*

# Copy all necessary files
COPY ./clue-builders/teastore/ .
# Copy configs
COPY ./clue-config.yaml .
COPY ./sut_configs/teastore.yaml .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Use Docker socket from host, so builder can invoke builds/pushes
VOLUME ["/var/run/docker.sock:/var/run/docker.sock"]

# Entrypoint
ENTRYPOINT ["python", "build.py"]