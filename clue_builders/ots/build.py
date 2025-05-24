#from config import Config
import os
import subprocess
import argparse
from config import Config

DEMO_VERSION = "clue-ots"
SUT_CONFIG = os.environ.get("SUT_CONFIG")
CLUE_CONFIG = os.environ.get("CLUE_CONFIG")

class OTSBuilder:
    def __init__(self, config, minimal: bool = False):
        self.config = config
        self.minimal = minimal
        self.sut_repo = "https://github.com/JulianLegler/opentelemetry-demo"
        self.docker_registry_address = "localhost:6789/clue"#config.sut_config.docker_registry_address
        self.image_version = "latest"
        self._set_envs()
    
    def check_docker_running(self):
        """
        Check if Docker is running.
        """
        try:
            subprocess.run(["docker", "info"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("Docker is running.")
        except subprocess.CalledProcessError:
            raise RuntimeError("Docker is not running. Please start Docker and try again.")

    def clone_repo(self):
        """
        Clone the OTS repository if it does not exist.
        """
        if not os.path.exists("opentelemetry-demo"):
            print("Cloning OTS repository...")
            subprocess.run(["git", "clone", self.sut_repo, "opentelemetry-demo"])
            print("OTS repository cloned successfully.")
        else:
            print("OTS repository already exists. Skipping clone.")

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
    config = Config(
        sut_config=SUT_CONFIG,
        clue_config=CLUE_CONFIG
    )
    builder = OTSBuilder(config, minimal=minimal)
    builder.check_docker_running()
    builder.clone_repo()
    builder.build()
    builder.push()

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Build OTS images")
    argparser.add_argument("--minimal", "-m", action="store_true", help="Build minimal OTS image")
    args = argparser.parse_args()


    main(minimal=args.minimal)
