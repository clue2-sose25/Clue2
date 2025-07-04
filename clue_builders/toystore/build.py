import os
import subprocess
import argparse
import re

DEMO_VERSION = "clue-toystore"
SUT_CONFIG = "/app/sut_configs/toystore.yaml"
CLUE_CONFIG = "/app/clue-config.yaml"
SUT_PATH = "toystore"

class ToystoreBuilder:
    def __init__(self):
        self.sut_repo = "https://github.com/clue2-sose25/sustainable_toystore"
        self.docker_registry_address = "registry:5000/clue"
        self.image_version = "latest"
        self.remote_platform_arch = "linux/arm64/v8"
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

    def check_buildx_available(self):
        """
        Check if Docker Buildx is available (it should be by default in modern Docker).
        """
        try:
            subprocess.run(["docker", "buildx", "version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("Docker Buildx is available.")
        except subprocess.CalledProcessError:
            raise RuntimeError("Docker Buildx is not available. Please update Docker to a recent version.")

    def _clone_repo(self):
        """
        Clone the SUT repository if it does not exist.
        """
        if not os.path.exists(SUT_PATH):
            print("Cloning SUT repository...")
            subprocess.run(["git", "clone", self.sut_repo, SUT_PATH], check=True)
            print("SUT repository cloned successfully.")
            self._update_docker_compose_registry()
        else:
            print("SUT repository already exists. Skipping clone.")
            self._update_docker_compose_registry()

    def _update_docker_compose_registry(self):
        """
        Update the docker-compose.yml file to use the local registry instead of ghcr.io.
        """
        compose_file_path = os.path.join(SUT_PATH, "docker-compose.yml")
        
        if not os.path.exists(compose_file_path):
            print("docker-compose.yml not found, skipping registry update.")
            return
        
        print("Updating docker-compose.yml to use local registry...")
        
        try:
            # Read the current docker-compose file
            with open(compose_file_path, 'r') as file:
                content = file.read()
                       
            # Pattern to match the ghcr.io image references
            pattern = r'ghcr\.io/clue2-sose25/sustainable_toystore/([^:]+):([^\s]+)'
            replacement = f'{self.docker_registry_address}/\\1:{self.image_version}'
            
            updated_content = re.sub(pattern, replacement, content)
            
            # Write the updated content back to the file
            with open(compose_file_path, 'w') as file:
                file.write(updated_content)
            
            print(f"Updated docker-compose.yml: replaced ghcr.io registry with {self.docker_registry_address}")
            
        except Exception as e:
            raise RuntimeError(f"Error updating docker-compose.yml registry: {e}")

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
    
    def build_and_push(self):
        """
        Build and push the SUT images using Docker Buildx with docker-compose.
        """
        print("Building and pushing SUT images using Buildx...")
        subprocess.run([
            "docker", "buildx", "bake",
            "--push",
            "--file", "docker-compose.yml"
        ], cwd=self.sut_path, check=True)
        print("SUT images built and pushed successfully using Buildx bake.")
    
    def build_push_loadgenerator(self):
        platform = (
            self.remote_platform_arch
        )
        registry = self.docker_registry_address

        print(f"Building Toystore workload generator for platform {platform}")
        tag = f"{registry}/toystore-loadgenerator"
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
            cwd=os.path.join("workload_generator"),
        )
        if build != 0:
            raise RuntimeError("Failed to build the workload generator")

        print(f"Built workload generator for platform {platform} and pushed to {tag}")


def main():
    """
    Main function to build and push the SUT image.
    """
    builder = ToystoreBuilder()
    builder.check_docker_running()
    builder.check_buildx_available()
    builder.build_and_push()
    builder.build_push_loadgenerator()

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Build SUT images using Docker Buildx")
    args = argparser.parse_args()
    main()