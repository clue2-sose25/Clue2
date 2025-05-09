import sys
from pathlib import Path
import docker
import subprocess
from os import path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
SOURCE_CODE_BASE = Path(__file__).resolve().parent.parent.parent
# allow importing from the parent directory
sys.path.append(str(SOURCE_CODE_BASE))
from config import Config
CONFIG_PATH = BASE_DIR.joinpath("clue-config.yaml")
SUT_CONFIG_PATH = BASE_DIR / "sut_configs" / "teastore-config.yaml"
RUN_CONFIG = Config(SUT_CONFIG_PATH, CONFIG_PATH)

def build():
    sut_path = RUN_CONFIG.sut_config.sut_path
    experiments = RUN_CONFIG.experiments_config.experiments
    remote_platform_arch = RUN_CONFIG.clue_config.remote_platform_arch
    docker_registry_address = RUN_CONFIG.clue_config.docker_registry_address
    docker_client = docker.from_env()

    # check if docker is running
    try:
        docker_client.ping()
    except docker.errors.NotFound:  
        raise RuntimeError("Docker is not running. Please start Docker and try again.")

    #for every branch, build the docker image
    for experiment in experiments:
        branch_name = experiment.target_branch
        switchBranch(sut_path, branch_name)
        deploy_maven_container(sut_path, docker_client)
        patch_buildx(sut_path, remote_platform_arch)
        build_docker_image(sut_path, docker_registry_address, branch_name)

def build_docker_image(sut_path, docker_registry_address, branch_name):
    print(f"Running the build_docker.sh")
    build = subprocess.check_call(
            ["sh", "build_docker.sh", "-r", f"{docker_registry_address}/", "-p"],
            cwd=path.join(sut_path, "tools"),
        )
        
    if build != 0:
        raise RuntimeError(
                "failed to build docker images. Run build_docker.sh manually and see why it fails"
            )

    print(f"Finished building images for {branch_name} branch, pushed to {docker_registry_address}")

def patch_buildx(sut_path, remote_platform_arch):
    print(f"Patching the build_docker.sh to use buildx allowing multi-arch builds")
    with open(path.join(sut_path, "tools", "build_docker.sh"), "r") as f:
        script = f.read()

    if "buildx" in script:
        print("buildx already used")
    else:
        script = script.replace(
                "docker build",
                f"docker buildx build --platform {remote_platform_arch}",
            )
        with open(path.join(sut_path, "tools", "build_docker.sh"), "w") as f:
            f.write(script)

def deploy_maven_container(sut_path, docker_client):
    print(f"Deploying the maven container for building teastore. Might take a while...")
        
    mvn_output = docker_client.containers.run(
            image="maven",
            auto_remove=True,
            volumes={
                path.abspath(path.join(sut_path)): {
                    "bind": "/mnt",
                    "mode": "rw",
                }
            },
            working_dir="/mnt",
            command="bash -c 'apt-get update && apt-get install -y dos2unix && find . -type f -name \"*.sh\" -exec dos2unix {} \\; && mvn clean install -DskipTests'",
        )
    if "BUILD SUCCESS" not in mvn_output.decode("utf-8"):
        print(mvn_output)
        raise RuntimeError(
                "failed to build teastore. Run mvn clean install -DskipTests manually and see why it fails"
            )
    else:
        print("Finished rebuiling java deps")

def switchBranch(sut_path, branch_name):
    git = subprocess.check_call(
            ["git", "switch", branch_name], cwd=path.join(sut_path)
        )
    if git != 0:
        raise RuntimeError(f"failed to switch git to {branch_name}")
        
    print(f"Using the {branch_name} branch")
    return branch_name

if __name__ == "__main__":
    build()
