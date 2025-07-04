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
            self.sut_config = yaml.safe_load(sut_file)["config"]
        
        with open(CLUE_CONFIG, 'r') as clue_file:
            self.clue_config = yaml.safe_load(clue_file)["config"]

        self.sut_repo = self.sut_config.get('sut_git_repo', '')
        self.docker_registry_address = self.clue_config.get('docker_registry_address', 'registry:5000/clue')
        self.platform = self.clue_config.get('remote_platform_arch', 'linux/amd64')
        self.minimal = minimal
        self.image_version = "latest"
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
    
    def build(self):
        """
        Build the OTS image using Docker.
        """
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

        
    def build_push_loadgenerator(self):
        platform = (
            self.platform
        )
        registry = self.docker_registry_address

        print(f"Building OTS workload generator for platform {platform}")
        tag = f"{registry}/ots-loadgenerator"
        build = subprocess.check_call(
            [
                "docker",
                "buildx",
                "build",
                "--platform", platform,
                "--push",
                "-t", tag,
                ".",
            ],
            cwd=path.join("workload_generator"),
        )
        if build != 0:
            raise RuntimeError("Failed to build the workload generator")

        print(f"Built workload generator for platform {platform} and pushed to {tag}")
    
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
    builder.build_push_loadgenerator()

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Build OTS images")
    argparser.add_argument("--minimal", "-m", action="store_true", help="Build minimal OTS image")
    args = argparser.parse_args()


    main(minimal=args.minimal)
