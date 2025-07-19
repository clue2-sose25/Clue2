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

    print(f"Building clue load generator for platform {remote_platform_arch}")
    tag = f"{docker_registry_address}/clue2-loadgenerator:latest"
    
    build_context = "/app/clue_loadgenerator"
    dockerfile_path = "/app/clue_loadgenerator/workload_generator/Dockerfile"
    cwd = "/app"
    
    build_command = [
        "docker",
        "buildx",
        "build",
        "--platform", remote_platform_arch,
        "--push",
        "-t", tag,
        "-f", dockerfile_path,
        build_context,
    ]
    
    print(f"Executing command: {' '.join(build_command)}")
    print(f"Working directory: {cwd}")
    
    build_result = subprocess.check_call(
        build_command,
        cwd=cwd,
    )
    
    if build_result != 0:
        raise RuntimeError("Failed to build the load generator")

    print(f"Built clue load generator for platform {remote_platform_arch} and pushed to {tag}")

if __name__ == "__main__":
    build()
