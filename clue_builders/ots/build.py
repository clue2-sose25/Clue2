#from config import Config
import os
import subprocess
import argparse

DEMO_VERSION = "clue-ots"

class OTSBuilder:
    def __init__(self, config = "config", minimal: bool = False):
        self.config = config
        self.minimal = minimal
        self.sut_path = "/home/leonardo/Studium/cloud_prototyping/opentelemetry-demo"
        self.docker_registry_address = "localhost:6789/clue"#config.sut_config.docker_registry_address
        self.image_version = "latest"
        self._set_envs()

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



if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Build OTS images")
    argparser.add_argument("--minimal", "-m", action="store_true", help="Build minimal OTS image")
    argparser.add_argument("--skip-build", "-s", action="store_true", help="Skip building the OTS image")
    args = argparser.parse_args()


    #config = Config()
    builder = OTSBuilder(minimal =args.minimal)
    if not args.skip_build:
        builder.build()
    
    builder.push()
