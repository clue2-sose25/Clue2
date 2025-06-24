#!/bin/sh
set -e

# Set DNS for the container
echo "nameserver 8.8.8.8" > /etc/resolv.conf

# Start Docker daemon with the same DNS and insecure registry
dockerd-entrypoint.sh --dns 8.8.8.8 --insecure-registry registry:5000 &

# Wait until the docker daemon is ready
while ! docker info >/dev/null 2>&1; do
  sleep 0.2
done

# Invoke your builder script
exec python3 /app/build.py