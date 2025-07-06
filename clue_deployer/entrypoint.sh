#!/bin/sh
set -e
# Environment variable fallbacks
: "${DEPLOY_AS_SERVICE:=false}"
: "${DEPLOY_ONLY:=false}"
: "${PATCH_LOCAL_CLUSTER:=true}"
: "${CLUSTER_PROXY_COMMAND:=}"


# Print configs 
echo "[ENTRYPOINT.SH] Starting CLUE Deployer container"
echo "[ENTRYPOINT.SH] Deploying as a service: $DEPLOY_AS_SERVICE"
echo "[ENTRYPOINT.SH] Deploy without benchmarking: $DEPLOY_ONLY"
echo "[ENTRYPOINT.SH] Patch kubeconfig: $PATCH_LOCAL_CLUSTER"
echo "[ENTRYPOINT.SH] Bechmark config: SUT: $SUT, experiment: $VARIANTS"

# Prepare the kubeconfig to allow access to clusters running on the host
echo "[ENTRYPOINT.SH] Preparing kubeconfig..."
python3 /app/clue_deployer/prepare_kubeconfig.py
if [ -f /app/clue_deployer/kubeconfig_patched ]; then
    chmod 600 /app/clue_deployer/kubeconfig_patched
    export KUBECONFIG=/app/clue_deployer/kubeconfig_patched
fi

# Start optional cluster proxy after kubeconfig was prepared
if [ -n "$CLUSTER_PROXY_COMMAND" ]; then
    echo "[ENTRYPOINT.SH] Starting SSH proxy: $CLUSTER_PROXY_COMMAND"
    [ -f /root/.ssh/id_rsa ] && chmod 600 /root/.ssh/id_rsa
    bash -c "$CLUSTER_PROXY_COMMAND &"
    echo "Starting with CLUSTER_PROXY_COMMAND: $CLUSTER_PROXY_COMMAND"
fi

# If DEPLOY_AS_SERVICE = True, deploy CLUE as a service
if [ "$DEPLOY_AS_SERVICE" = "true" ]; then
    echo "[ENTRYPOINT.SH] Starting FastAPI service..."
    exec uvicorn clue_deployer.src.service.service:app --host 0.0.0.0 --port 8000
    exit 0
fi

# Deploy CLUE
# Uncomment the line below to enable debugging with debugpy
#exec uv run -m debugpy --listen 0.0.0.0:5678 --wait-for-client clue_deployer/src/main.py
echo "Starting without DEPLOY_AS_SERVICE "
exec uv run clue_deployer/src/main.py