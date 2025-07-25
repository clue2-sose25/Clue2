#!/bin/sh
set -e

# Environment variable fallbacks
: "${DEPLOY_AS_SERVICE:=false}"
: "${DEPLOY_ONLY:=false}"
: "${PATCH_LOCAL_CLUSTER:=false}"
: "${CLUSTER_PROXY_COMMAND:=}"
: "${SSH_KEY_FILE_PATH:=/root/.ssh/id_rsa}"
: "${PRECONFIGURE_CLUSTER:=false}"
: "${HELM_DRIVER:=configmap}"
: "${SETUP_GRAFANA_DASHBOARD:=false}"
: "${ENABLE_DEBUG:=false}"

# Print configs 
echo "[ENTRYPOINT.SH] Starting CLUE Deployer container"
echo "[ENTRYPOINT.SH] Deploying as a service: $DEPLOY_AS_SERVICE"
echo "[ENTRYPOINT.SH] Deploy without benchmarking: $DEPLOY_ONLY"
if [ -n "$KUBERNETES_SERVICE_HOST" ]; then
    PATCH_LOCAL_CLUSTER=false
fi
echo "[ENTRYPOINT.SH] Patch kubeconfig: $PATCH_LOCAL_CLUSTER"
echo "[ENTRYPOINT.SH] Bechmark config: SUT: $SUT, experiment: $VARIANTS"
echo "[ENTRYPOINT.SH] Debugging enabled: $ENABLE_DEBUG"

# Prepare the kubeconfig to allow access to clusters running on the host or in a local cluster
if [ -z "$KUBERNETES_SERVICE_HOST" ]; then
    echo "[ENTRYPOINT.SH] Preparing kubeconfig..."
    python3 /app/clue_deployer/prepare_kubeconfig.py
    if [ -f /app/clue_deployer/kubeconfig_patched ]; then
        chmod 600 /app/clue_deployer/kubeconfig_patched
        export KUBECONFIG=/app/clue_deployer/kubeconfig_patched
    fi
else
    echo "[ENTRYPOINT.SH] Running in cluster, skipping kubeconfig preparation."
fi

# Start optional cluster proxy after kubeconfig was prepared and outside of the cluster
if [ -n "$CLUSTER_PROXY_COMMAND" ] && [ -z "$KUBERNETES_SERVICE_HOST" ]; then
    echo "[ENTRYPOINT.SH] Starting SSH proxy: ssh -i $SSH_KEY_FILE_PATH $CLUSTER_PROXY_COMMAND"
    ls -l "$SSH_KEY_FILE_PATH"
    if [ -f "$SSH_KEY_FILE_PATH" ]; then
        chmod 400 "$SSH_KEY_FILE_PATH" || true
        ls -l "$SSH_KEY_FILE_PATH"
    fi
    echo "Checking SSH key file permissions..."
    ssh -i "$SSH_KEY_FILE_PATH" $CLUSTER_PROXY_COMMAND &
    echo "Starting with CLUSTER_PROXY_COMMAND: $CLUSTER_PROXY_COMMAND"
elif [ -n "$CLUSTER_PROXY_COMMAND" ]; then
    echo "[ENTRYPOINT.SH] Running in cluster, ignoring CLUSTER_PROXY_COMMAND"
fi

# If DEPLOY_AS_SERVICE = True, deploy CLUE as a service
# If DEPLOY_AS_SERVICE = True, deploy CLUE as a service
if [ "$DEPLOY_AS_SERVICE" = "true" ]; then
    if [ "$ENABLE_DEBUG" = "true" ]; then
        echo "[ENTRYPOINT.SH] Starting FastAPI service with debugging..."
        exec python3 -Xfrozen_modules=off -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m uvicorn clue_deployer.src.service.service:app --host 0.0.0.0 --port 8000
    else
        echo "[ENTRYPOINT.SH] Starting FastAPI service without debugging..."
        exec uvicorn clue_deployer.src.service.service:app --host 0.0.0.0 --port 8000
    fi
    exit 0
fi

# Deploy CLUE
if [ "$ENABLE_DEBUG" = "true" ]; then
    echo "[ENTRYPOINT.SH] Starting CLUE deployer with debugging..."
    exec uv run -m debugpy --listen 0.0.0.0:5678 --wait-for-client clue_deployer/src/main.py
else
    echo "[ENTRYPOINT.SH] Starting CLUE deployer without debugging..."
    exec uv run clue_deployer/src/main.py
fi