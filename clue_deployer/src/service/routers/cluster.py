import os
import base64
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

KUBECONFIG_PATCHED = "/app/clue_deployer/kubeconfig_patched"

router = APIRouter()

class KubeConfigRequest(BaseModel):
    kubeconfig: str
    patch_local_cluster: bool = True

@router.post("/api/cluster/config")
async def upload_kubeconfig(req: KubeConfigRequest):
    """Upload kubeconfig and optionally patch localhost addresses."""
    try:
        decoded = base64.b64decode(req.kubeconfig).decode()
        config = yaml.safe_load(decoded)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to decode kubeconfig: {exc}")

    if req.patch_local_cluster:
        for cluster in config.get("clusters", []):
            server = cluster["cluster"].get("server", "")
            if "127.0.0.1" in server or "localhost" in server:
                cluster["cluster"]["server"] = (
                    server.replace("127.0.0.1", "clue-cluster-control-plane")
                    .replace("localhost", "clue-cluster-control-plane")
                )
                cluster["cluster"].pop("certificate-authority", None)
                cluster["cluster"].pop("certificate-authority-data", None)
                cluster["cluster"]["insecure-skip-tls-verify"] = True

    try:
        with open(KUBECONFIG_PATCHED, "w") as f:
            yaml.safe_dump(config, f)
        os.environ["KUBECONFIG"] = KUBECONFIG_PATCHED
        os.environ["PATCH_LOCAL_CLUSTER"] = "true" if req.patch_local_cluster else "false"
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save kubeconfig: {exc}")
    return {"message": "kubeconfig uploaded"}

@router.get("/api/cluster/status")
async def cluster_status():
    """Check if kubeconfig has been uploaded."""
    configured = os.path.isfile(KUBECONFIG_PATCHED)
    patch_local = os.getenv("PATCH_LOCAL_CLUSTER", "true").lower() == "true"
    return {"configured": configured, "patch_local_cluster": patch_local}