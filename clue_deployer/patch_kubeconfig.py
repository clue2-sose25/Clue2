import os
import sys
import base64
import yaml

DEFAULT_KUBECONFIG = "/root/.kube/config"
KUBECONFIG_PATCHED = "/app/clue_deployer/kubeconfig_patched"

def load_config():
    kube_b64 = os.getenv("KUBE_CONFIG")
    kube_path = os.getenv("KUBECONFIG_FILE", DEFAULT_KUBECONFIG)

    if kube_b64:
        try:
            decoded = base64.b64decode(kube_b64).decode()
            return yaml.safe_load(decoded)
        except Exception as exc:
            print(f"[PATCH_KUBECONFIG] Failed to decode KUBE_CONFIG: {exc}")
            sys.exit(1)

    if not os.path.exists(kube_path):
        print(f"[PATCH_KUBECONFIG] No kubeconfig found at {kube_path}")
        sys.exit(1)
    with open(kube_path) as f:
        return yaml.safe_load(f)


def patch_kubeconfig():
    config = load_config()
    changed = False
    for cluster in config.get("clusters", []):
        server = cluster["cluster"].get("server", "")
        if "127.0.0.1" in server or "localhost" in server:
            cluster["cluster"]["server"] = server.replace("127.0.0.1", "clue-cluster-control-plane").replace("localhost", "clue-cluster-control-plane")
            # Remove cert fields and set insecure-skip-tls-verify
            cluster["cluster"].pop("certificate-authority", None)
            cluster["cluster"].pop("certificate-authority-data", None)
            cluster["cluster"]["insecure-skip-tls-verify"] = True
            changed = True

    with open(KUBECONFIG_PATCHED, "w") as f:
        yaml.safe_dump(config, f)

    os.environ["KUBECONFIG"] = KUBECONFIG_PATCHED
    if changed:
        print(
            "[PATCH_KUBECONFIG] Patched kubeconfig to use clue-cluster-control-plane "
            "and insecure-skip-tls-verify: true"
        )

if __name__ == "__main__":
    patch_kubeconfig()