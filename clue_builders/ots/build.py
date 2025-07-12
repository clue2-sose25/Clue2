import os
import subprocess
import argparse
import yaml
from os import path

DEMO_VERSION = "clue-ots"
SUT_CONFIG = "/app/sut_configs/otel-demo.yaml"
CLUE_CONFIG = "/app/clue-config.yaml"
SUT_PATH = "opentelemetry-demo"

class OTSBuilder:
    def __init__(self, minimal: bool = False, ):
        with open(SUT_CONFIG, 'r') as sut_file:
            sut_yaml = yaml.safe_load(sut_file)
            self.sut_config = sut_yaml["config"]
            self.variants = sut_yaml.get('variants', [])
        
        with open(CLUE_CONFIG, 'r') as clue_file:
            self.clue_config = yaml.safe_load(clue_file)["config"]

        self.sut_repo = self.sut_config.get('sut_git_repo', '')
        self.docker_registry_address = self.clue_config.get('docker_registry_address', 'registry:5000/clue')
        self.platform = self.clue_config.get('remote_platform_arch', 'linux/amd64')
        self.minimal = minimal
        exp_name = os.environ.get("OTS_EXP_NAME", "baseline")
        # search target branch for exp_name
        target_branch = None
        for variant in self.variants:
            if variant.get('name') == exp_name:
                target_branch = variant.get('target_branch')
                break
        
        if target_branch is None:
            raise ValueError(f"No variant found with name '{exp_name}' in SUT config")

        self.image_version = target_branch
        self._set_envs()
        self._clone_repo()
        self.sut_path = SUT_PATH
    
    
    
    def check_docker_running(self):
        """
        Check if Docker is running.
        """
        try:
            subprocess.run(["docker", "info"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("Docker is running.")
        except subprocess.CalledProcessError:
            raise RuntimeError("Docker is not running. Please start Docker and try again.")

    def _clone_repo(self):
        """
        Clone the OTS repository if it does not exist.
        """
        if not os.path.exists(SUT_PATH):
            print("Cloning OTS repository...")
            subprocess.run(["git", "clone", self.sut_repo, SUT_PATH], check=True)
            print("OTS repository cloned successfully.")
        else:
            print("OTS repository already exists. Skipping clone.")

    def _set_envs(self):
        """
        overwrite the environment variables 
        """
        os.environ["IMAGE_NAME"] = self.docker_registry_address + "/otel-demo"
        os.environ["IMAGE_VERSION"] = self.image_version
        os.environ["DEMO_VERSION"] = DEMO_VERSION

        print("Environment variables set:")
        print(f"IMAGE_NAME: {os.environ['IMAGE_NAME']}")
        print(f"IMAGE_VERSION: {os.environ['IMAGE_VERSION']}")
    
    def patch_compose_images(self, compose_path: str):
        """
        Patch the docker-compose file so each service image is set to its own repo (e.g., registry:5000/clue/ots-<service>:latest)
        """
        import yaml
        with open(compose_path, 'r') as f:
            compose = yaml.safe_load(f)

        services = compose.get('services', {})
        for svc_name, svc in services.items():
            # Only patch services that use IMAGE_NAME/DEMO_VERSION
            image = svc.get('image', '')
            if '${IMAGE_NAME}' in image and '${DEMO_VERSION}-' in image:
                # Extract service suffix (e.g., frontend, cart, etc.)
                suffix = image.split('${DEMO_VERSION}-')[-1]
                new_image = f"{self.docker_registry_address}/ots-{suffix}:{self.image_version}"
                svc['image'] = new_image
        with open(compose_path, 'w') as f:
            yaml.dump(compose, f, default_flow_style=False)
        print(f"Patched compose file: {compose_path}")

    def build(self):
        """
        Build the OTS image using Docker.
        """
        # Patch the compose file before building
        compose_path = os.path.join(self.sut_path, 'docker-compose.yml')
        self.patch_compose_images(compose_path)
        try:
            if self.minimal:
                print("Building minimal OTS image...")
                subprocess.run(
                    ["docker", "compose", "-f", "docker-compose.minimal.yml", "build", ]
                    , cwd=self.sut_path
                )
            else:
                print("Building OTS image...")
                subprocess.run(
                    ["docker", "compose", "build"]
                    , cwd=self.sut_path
                )
            print("OTS image built successfully.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error building OTS image: {e}")

        
    def push(self):
        """
        Push the OTS image to the Docker registry.
        """
        try:
            if self.minimal:
                print("Pushing minimal OTS image to Docker registry...")
                subprocess.run(
                    ["docker", "compose", "-f", "docker-compose.minimal.yml", "push"]
                    , cwd=self.sut_path
                )
            else:
                print("Pushing OTS image to Docker registry...")
                subprocess.run(
                    ["docker", "compose", "push"]
                    , cwd=self.sut_path
                )
            print("OTS images pushed successfully.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error pushing OTS image: {e}")


def main(minimal: bool = False):
    """
    Main function to build and push the OTS image.
    """
    builder = OTSBuilder(minimal=minimal)
    builder.check_docker_running()
    builder.build()
    builder.push()

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Build OTS images")
    argparser.add_argument("--minimal", "-m", action="store_true", help="Build minimal OTS image")
    args = argparser.parse_args()


    main(minimal=args.minimal)
