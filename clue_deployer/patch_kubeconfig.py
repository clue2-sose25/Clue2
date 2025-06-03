import os
import sys
import yaml

KUBECONFIG_ORIG = "/root/.kube/config"
KUBECONFIG_PATCHED = "/app/clue_deployer/kubeconfig_patched"

def patch_kubeconfig():
    if not os.path.exists(KUBECONFIG_ORIG):
        print(f"No kubeconfig found at {KUBECONFIG_ORIG}")
        sys.exit(1)
    with open(KUBECONFIG_ORIG) as f:
        config = yaml.safe_load(f)

    changed = False
    for cluster in config.get("clusters", []):
        server = cluster["cluster"].get("server", "")
        if "127.0.0.1" in server or "localhost" in server:
            cluster["cluster"]["server"] = server.replace("127.0.0.1", "host.internal").replace("localhost", "host.internal")
            # Remove cert fields and set insecure-skip-tls-verify
            cluster["cluster"].pop("certificate-authority", None)
            cluster["cluster"].pop("certificate-authority-data", None)
            cluster["cluster"]["insecure-skip-tls-verify"] = True
            changed = True

    with open(KUBECONFIG_PATCHED, "w") as f:
        yaml.safe_dump(config, f)

    os.environ["KUBECONFIG"] = KUBECONFIG_PATCHED
    if changed:
        print("Patched kubeconfig to use host.internal and set insecure-skip-tls-verify: true")

if __name__ == "__main__":
    patch_kubeconfig()