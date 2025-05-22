#!/bin/sh
set -e

# Patch the kubeconfig to allow access to clusters running on the host
python3 /app/patch_kubeconfig.py

chmod 600 /app/kubeconfig_patched

export KUBECONFIG=/app/kubeconfig_patched

# IF DEPLOY_ONLY call the deployer script with the --deploy-only flag and exit
if [ "$DEPLOY_ONLY" = "true" ]; then
    echo "Deploying only, not executing any experiments"
    exec uv run clue_deployer/run.py --sut="$SUT" --exp-name="$EXPERIMENT"
    exit 0
fi

echo "Deploying and executing selected experiments"
# Check if the SUT is teastore
if [ "$SUT" = "teastore" ]; then
    # If teastore, run the teastore deployer script
    exec uv run clue_deployer/main.py --sut-path "/app/sut_configs/teastore.yaml" # --exp "$EXPERIMENT" # TODO no support for experiments yet
    exit 0
fi

echo "Unknown SUT, please update the entrypoint script to handle this case"