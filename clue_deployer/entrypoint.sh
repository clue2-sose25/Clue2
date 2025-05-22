#!/bin/sh
set -e

# Start Docker daemon, allowing our local registry as insecure (with interal port)
# dockerd-entrypoint.sh --insecure-registry registry:5000 &

# Patch the kubeconfig to allow access to clusters running on the host
python3 /app/patch_kubeconfig.py

chmod 600 /app/kubeconfig_patched

# Wait until the docker daemon is ready
while ! docker info >/dev/null 2>&1; do
  sleep 0.2
done

export KUBECONFIG=/app/kubeconfig_patched

# keep the container alive
tail -f >/dev/null

# Invoke your deployer script
#exec uv run clue_deployer/main.py