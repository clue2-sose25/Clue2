#!/bin/sh
set -e

# Patch the kubeconfig to allow access to clusters running on the host
python3 /app/patch_kubeconfig.py

chmod 600 /app/kubeconfig_patched

export KUBECONFIG=/app/kubeconfig_patched

# Invoke the deployer script with the SUT environment variable
exec uv run clue_deployer/run.py --sut="$SUT" --exp-name="$EXPERIMENT"