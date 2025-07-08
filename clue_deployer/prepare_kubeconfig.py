import os
import sys
import base64
import yaml

KUBECONFIG_ORIGINAL = "/root/.kube/config"
KUBECONFIG_PATCHED = "/app/clue_deployer/kubeconfig_patched"
PATCH_CONFIG = os.getenv("PATCH_LOCAL_CLUSTER")
CONFIG_B64 = os.getenv("KUBE_CONFIG")

# Load the config
def load_config():
    # If present, try to decode base64 config
    if CONFIG_B64:
        print("[PREPARE_KUBECONFIG] Detected Kube Config in B64 encoding. Decoding...")
        try:
            decoded = base64.b64decode(CONFIG_B64).decode()
            print("[PREPARE_KUBECONFIG] Successfully decoded the config.")
            return yaml.safe_load(decoded)
        except Exception as exc:
            print(f"[PREPARE_KUBECONFIG] Failed to decode KUBE_CONFIG: {exc}")
            sys.exit(1)
    # Else, use the provided config from the path
    if not os.path.exists(KUBECONFIG_ORIGINAL):
        print(f"[PREPARE_KUBECONFIG] No kubeconfig found at {KUBECONFIG_ORIGINAL}")
        sys.exit(1)
    # Return the config from the path
    print(f"[PREPARE_KUBECONFIG] No B64 config detected. Using the Kube config from the path: {KUBECONFIG_ORIGINAL}")
    with open(KUBECONFIG_ORIGINAL) as f:
        return yaml.safe_load(f)
# Patch the config
def _save_config(config):
    """Write the (possibly patched) config to the known path and export KUBECONFIG."""
    with open(KUBECONFIG_PATCHED, "w") as f:
        yaml.safe_dump(config, f)
    os.environ["KUBECONFIG"] = KUBECONFIG_PATCHED
    
# Patch the config
def patch_kubeconfig(config):
    for cluster in config.get("clusters", []):
        server = cluster["cluster"].get("server", "")
        if "127.0.0.1" in server or "localhost" in server:
            cluster["cluster"]["server"] = server.replace("127.0.0.1", "clue-cluster-control-plane").replace("localhost", "clue-cluster-control-plane")
            # Remove cert fields and set insecure-skip-tls-verify 
            cluster["cluster"].pop("certificate-authority", None)
            cluster["cluster"].pop("certificate-authority-data", None)
            cluster["cluster"]["insecure-skip-tls-verify"] = True
    # Save the changes
    _save_config(config)
    print("[PREPARE_KUBECONFIG] Patched kubeconfig to use clue-cluster-control-plane and insecure-skip-tls-verify: true")

if __name__ == "__main__":
    config = load_config()
    if PATCH_CONFIG and PATCH_CONFIG.lower() == "true":
        patch_kubeconfig(config)
    else:
        _save_config(config)
