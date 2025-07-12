import os
import subprocess
import argparse
import re
import yaml
import sys
# Add function to load YAML configs
def load_configs():
    # Load clue-config.yaml
    try:
        with open("clue-config.yaml", "r") as f:
            clue_config = yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: clue-config.yaml not found")
        sys.exit(1)
    
    try:
        with open("sut_configs/toystore.yaml", "r") as f:
            sut_config = yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: toystore.yaml not found")
        sys.exit(1)
        
    # Create a simple config object with the loaded data
    config = type('Config', (), {
        'clue_config': type('ClueConfig', (), {
            'remote_platform_arch': clue_config['config']['remote_platform_arch'],
            'docker_registry_address': clue_config['config']['docker_registry_address']
        })(),
        'sut_config': type('SutConfig', (), {
            'sut_path': sut_config['config']['sut_path'],
            'experiments': sut_config.get('variants', []),
            'sut_repo': sut_config['config']['sut_git_repo']
        })()
    })()
    return config

RUN_CONFIG = load_configs()

class ToystoreBuilder:

    def __init__(self):
        self.sut_repo = RUN_CONFIG.sut_config.sut_repo
        self.docker_registry_address = RUN_CONFIG.clue_config.docker_registry_address
        self.image_version = os.environ.get("TOYSTORE_EXP_NAME", "latest")
        self.remote_platform_arch = RUN_CONFIG.clue_config.remote_platform_arch
        self._set_envs()
        self._clone_repo()
        self.sut_path = RUN_CONFIG.sut_config.sut_path
    
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
    
def main():
    """
    Main function to build and push the SUT image.
    """
    builder = ToystoreBuilder()
    builder.check_docker_running()
    builder.check_buildx_available()
    builder.build_and_push()

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Build SUT images using Docker Buildx")
    args = argparser.parse_args()
    main()