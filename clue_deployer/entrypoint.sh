#!/bin/sh
set -e

# Patch the kubeconfig to allow access to clusters running on the host
python3 /app/patch_kubeconfig.py

chmod 600 /app/kubeconfig_patched

export KUBECONFIG=/app/kubeconfig_patched

# If DEPLOY_ONLY env. variable is true, call the deployer script without running the experiments
if [ "$DEPLOY_ONLY" = "true" ]; then
    echo "Deploying the SUT without executing any experiments"
    exec uv run clue_deployer/run.py
    exit 0
fi

if [ "$AS_SERVICE" = "true" ]; then
    echo "Starting FastAPI service..."
    exec fastapi dev service.py --host 0.0.0.0 --port 8000
    exit 0
fi
# Deploy the specified SUT and experiment
echo "Deploying and executing selected SUT experiments"
exec uv run clue_deployer/main.py
