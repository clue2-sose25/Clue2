import os, yaml, time, pathlib
from kubernetes import client, config, watch

# --- env vars set by the Job ------------------------------------------------
SUT_NS  = os.getenv("SUT_NS",  "sut-demo")
SA_NAME = os.getenv("SA_NAME", "sut-runner")
IMG     = f"{os.getenv('IMAGE_REPO')}/{os.getenv('IMAGE_NAME')}:{os.getenv('IMAGE_TAG')}"
NODESEL = os.getenv("NODE_SELECTOR", "")
PORT     = os.getenv("APP_PORT", "80")

TEMPLATE = pathlib.Path("/app/manifests/sibling_pod.yaml").read_text()
MANIFEST = yaml.safe_load(
    TEMPLATE.replace("{{NS}}", SUT_NS)
            .replace("{{SA_NAME}}", SA_NAME)
            .replace("{{IMAGE}}", IMG)
            .replace("{{NODE_SELECTOR}}", NODESEL)
            .replace("{{APP_PORT}}", PORT))

def main():
    try: config.load_incluster_config()
    except config.ConfigException: config.load_kube_config()
    api = client.CoreV1Api()
    api.create_namespaced_pod(SUT_NS, MANIFEST)
    for ev in watch.Watch().stream(api.list_namespaced_pod,
                                   namespace=SUT_NS,
                                   field_selector="metadata.name=sut-app"):
        if ev["object"].status.phase == "Running":
            print("Sibling pod is Running.")
            break
        time.sleep(1)

if __name__ == "__main__":
    main()
