#!/bin/sh
set -e

# Patch the kubeconfig to allow access to clusters running on the host
python3 /app/patch_kubeconfig.py

chmod 600 /app/kubeconfig_patched

export KUBECONFIG=/app/kubeconfig_patched

# keep the container alive
tail -f >/dev/null

# Invoke your deployer script
#exec uv run clue_deployer/main.py