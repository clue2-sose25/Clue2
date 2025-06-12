#!/bin/sh
set -e
# Environment variable fallbacks
: "${DEPLOY_AS_SERVICE:=false}"
: "${DEPLOY_ONLY:=false}"

# Print configs
echo "[ENTRYPOINT.SH] Starting CLUE Deployer container"
echo "[ENTRYPOINT.SH] Deploying as a service: $DEPLOY_AS_SERVICE"
echo "[ENTRYPOINT.SH] Deploy without benchmarking: $DEPLOY_ONLY"
echo "[ENTRYPOINT.SH] Bechmark config: SUT: $SUT_NAME, experiment: $EXPERIMENT_NAME"

# Patch the kubeconfig to allow access to clusters running on the host
python3 /app/clue_deployer/patch_kubeconfig.py
chmod 600 /app/clue_deployer/kubeconfig_patched
export KUBECONFIG=/app/clue_deployer/kubeconfig_patched

# If DEPLOY_AS_SERVICE = True, deploy CLUE as a service
if [ "$DEPLOY_AS_SERVICE" = "true" ]; then
    echo "[ENTRYPOINT.SH] Starting FastAPI service..."
    exec uvicorn clue_deployer.src.service.service:app --host 0.0.0.0 --port 8000
    exit 0
fi

# Deploy CLUE
# Uncomment the line below to enable debugging with debugpy
#exec uv run -m debugpy --listen 0.0.0.0:5678 --wait-for-client clue_deployer/src/main.py
exec uv run clue_deployer/src/main.py
