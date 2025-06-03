#!/bin/sh
set -e
# Environment variable fallbacks
: "${AS_SERVICE:=false}"
: "${DEPLOY_ONLY:=false}"


echo "Starting with deploy $DEPLOY_ONLY, service_type $AS_SERVICE, and SUT: $SUT_NAME, Experiment: $EXPERIMENT_NAME if defined :/"

# Patch the kubeconfig to allow access to clusters running on the host
python3 /app/clue_deployer/patch_kubeconfig.py

chmod 600 /app/clue_deployer/kubeconfig_patched

export KUBECONFIG=/app/kubeconfig_patched

# If DEPLOY_ONLY env. variable is true, call the deployer script without running the experiments
if [ "$DEPLOY_ONLY" = "true" ]; then
    echo "Deploying the SUT without executing any experiments"
    exec uv run clue_deployer/src/run.py
    exit 0
fi

if [ "$AS_SERVICE" = "true" ]; then
    echo "Starting FastAPI service..."
    exec uvicorn clue_deployer.service.service:app --host 0.0.0.0 --port 8000
    exit 0
fi
# Deploy the specified SUT and experiment
echo "Deploying and executing selected SUT experiments"
exec uv run clue_deployer/src/main.py
