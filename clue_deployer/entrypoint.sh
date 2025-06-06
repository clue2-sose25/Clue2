#!/bin/sh
set -e
# Environment variable fallbacks
: "${DEPLOY_AS_SERVICE:=false}"
: "${DEPLOY_ONLY:=false}"

echo "Starting CLUE Deployer..."
echo "Deploying as a service: $DEPLOY_AS_SERVICE"
echo "Deploy without benchmarking: $DEPLOY_ONLY"
echo "Bechmark config: SUT: $SUT_NAME, experiment: $EXPERIMENT_NAME"

# Patch the kubeconfig to allow access to clusters running on the host
python3 /app/clue_deployer/patch_kubeconfig.py

chmod 600 /app/clue_deployer/kubeconfig_patched

export KUBECONFIG=/app/clue_deployer/kubeconfig_patched

# If DEPLOY_AS_SERVICE = True, deploy CLUE as a service
if [ "$DEPLOY_AS_SERVICE" = "true" ]; then
    echo "Starting FastAPI service..."
    exec uvicorn clue_deployer.service.service:app --host 0.0.0.0 --port 8000
    exit 0
fi

# If DEPLOY_ONLY = True, deploy CLUE as a script without running the experiments
if [ "$DEPLOY_ONLY" = "true" ]; then
    echo "Deploying the SUT without executing any experiments"
    exec uv run clue_deployer/src/run.py
    exit 0
else
    # Deploy CLUE as a script with benchmarking
    echo "Deploying and executing selected SUT experiments"
    # Uncomment the line below to enable debugging with debugpy
    #exec uv run -m debugpy --listen 0.0.0.0:5678 --wait-for-client clue_deployer/src/main.py
    exec uv run clue_deployer/src/main.py
    exit 0
fi