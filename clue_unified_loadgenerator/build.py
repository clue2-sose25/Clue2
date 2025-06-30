import os
from os import path
import sys
import subprocess
import yaml
import docker

def load_clue_config():
    # Load clue-config.yaml
    try:
        with open("clue-config.yaml", "r") as f:
            clue_config = yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: clue-config.yaml not found")
        sys.exit(1)
    
    # Create a simple config object with the loaded data
    config = type('Config', (), {
        'remote_platform_arch': clue_config['config']['remote_platform_arch'],
        'docker_registry_address': clue_config['config']['docker_registry_address']
    })()
    
    return config

RUN_CONFIG = load_clue_config()

def build():
    remote_platform_arch = RUN_CONFIG.remote_platform_arch
    docker_registry_address = RUN_CONFIG.docker_registry_address
    docker_client = docker.from_env()

    try:
        docker_client.ping()
    except docker.errors.NotFound:  
        raise RuntimeError("Docker is not running. Please start Docker and try again.")

    print(f"Building unified load generator for platform {remote_platform_arch}")
    tag = f"{docker_registry_address}/unified-loadgenerator:latest"
    
    build_command = [
        "docker",
        "buildx",
        "build",
        "--platform", remote_platform_arch,
        "--push",
        "-t", tag,
        "./clue_unified_loadgenerator", # Specify the directory containing the Dockerfile
    ]
    
    print(f"Executing command: {' '.join(build_command)}")
    
    build_result = subprocess.check_call(
        build_command,
        cwd=path.dirname(path.abspath(__file__)), # Set CWD to the directory of this script (/app)
    )
    
    if build_result != 0:
        raise RuntimeError("Failed to build the unified load generator")

    print(f"Built unified load generator for platform {remote_platform_arch} and pushed to {tag}")

if __name__ == "__main__":
    build()
