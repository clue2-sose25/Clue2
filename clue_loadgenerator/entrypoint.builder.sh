#!/bin/sh
set -e

# Start Docker daemon, allowing our local registry as insecure (with interal port) 
dockerd-entrypoint.sh --insecure-registry registry:5000 &

# Wait until the docker daemon is ready
while ! docker info >/dev/null 2>&1; do
  sleep 0.2
done

# Invoke your builder script
python3 /app/build.py
