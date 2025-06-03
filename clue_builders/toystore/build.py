import os
import subprocess
import argparse
from config import Config

DEMO_VERSION = "clue-toystore"
SUT_CONFIG = "/app/sut_configs/toystore.yaml"
CLUE_CONFIG = "/app/clue-config.yaml"
SUT_PATH = "toystore"

class ToystoreBuilder:
    def __init__(self, config):
        self.config = config
        self.sut_repo = config.sut_config.sut_git_repo
        self.docker_registry_address = "registry:5000/clue"
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
        Clone the SUT repository if it does not exist.
        """
        if not os.path.exists(SUT_PATH):
            print("Cloning SUT repository...")
            subprocess.run(["git", "clone", self.sut_repo, SUT_PATH], check=True)
            print("SUT repository cloned successfully.")
        else:
            print("SUT repository already exists. Skipping clone.")

    def _set_envs(self):
        """
        overwrite the environment variables 
        """
        os.environ["IMAGE_NAME"] = self.docker_registry_address
        os.environ["IMAGE_VERSION"] = self.image_version
        os.environ["DEMO_VERSION"] = DEMO_VERSION

        print("Environment variables set:")
        print(f"IMAGE_NAME: {os.environ['IMAGE_NAME']}")
        print(f"IMAGE_VERSION: {os.environ['IMAGE_VERSION']}")
    
    def build(self):
        """
        Build the SUT image using Docker.
        """
        try:
            print("Building SUT image...")
            subprocess.run(
                ["docker", "compose", "build"]
                , cwd=self.sut_path
            )
            print("SUT image built successfully.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error building SUT image: {e}")

        
    def push(self):
        """
        Push the SUT image to the Docker registry.
        """
        try:
            print("Pushing SUT image to Docker registry...")
            subprocess.run(
                ["docker", "compose", "push"]
                , cwd=self.sut_path
            )
            print("SUT images pushed successfully.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error pushing SUT image: {e}")


def main():
    """
    Main function to build and push the SUT image.
    """
    config = Config(
        sut_config=SUT_CONFIG,
        clue_config=CLUE_CONFIG
    )
    builder = ToystoreBuilder(config)
    builder.check_docker_running()
    builder.build()
    builder.push()

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Build SUT images")
    args = argparser.parse_args()


    main()
