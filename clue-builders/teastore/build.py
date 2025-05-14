import os
import sys
from pathlib import Path
import docker
import subprocess
from os import path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SOURCE_CODE_BASE = Path(__file__).resolve().parent.parent.parent.joinpath("clue-deployer")

# allow importing from the parent directory
sys.path.append(str(SOURCE_CODE_BASE))

from config import Config
from experiment_list import ExperimentList
from experiment import Experiment

CONFIG_PATH = BASE_DIR.joinpath("clue-config.yaml")
SUT_CONFIG_PATH = BASE_DIR / "sut_configs" / "teastore.yaml"
RUN_CONFIG = Config(SUT_CONFIG_PATH, CONFIG_PATH)

def build(experiment: Experiment):
    sut_path = RUN_CONFIG.sut_config.sut_path
    remote_platform_arch = RUN_CONFIG.clue_config.remote_platform_arch
    docker_registry_address = RUN_CONFIG.clue_config.docker_registry_address
    docker_client = docker.from_env()

    # check if docker is running
    try:
        docker_client.ping()
    except docker.errors.NotFound:  
        raise RuntimeError("Docker is not running. Please start Docker and try again.")
    
    # Clone the sustainable_teastore repository if it doesn't exist
    teastore_path = path.join(sut_path, "teastore")
    if not path.exists(teastore_path):
        subprocess.check_call(["git", "clone", "https://github.com/ISE-TU-Berlin/sustainable_teastore.git", "teastore"], cwd=sut_path)
        print("Cloned sustainable_teastore repository")
    
    branch_name = experiment.target_branch
    switchBranch(teastore_path, branch_name)
    deploy_maven_container(sut_path, docker_client)
    patch_buildx(sut_path, remote_platform_arch)
    build_docker_image(sut_path, docker_registry_address, branch_name)

def check_docker_all_images_exist(registry_address):
    docker_client = docker.from_env()
    # read all images planned to build from sut_path/tools/build_docker.sh
    with open(path.join(RUN_CONFIG.sut_config.sut_path, "tools", "build_docker.sh"), "r") as f:
        script = f.read()
        # get image only name from push command: docker push "${registry}teastore-db"
        images = [line.split(" ")[-1].split("/")[-1] for line in script.split("\n") if "docker push" in line]
        images = [image.split(":")[0] for image in images]
        images = [image.removeprefix("\"${registry}").removesuffix("\"") for image in images]
        # check if the image exists in the local docker registry
        for image in images:
            try:
                docker_client.images.get_registry_data(f"{registry_address}/{image}")
            except docker.errors.APIError:
                print(f"Image {image} not found in {registry_address} - rebuilding all images")
                return False
        print("All images found in local docker registry")
        return True

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

def build_workload(experiment: Experiment):
        docker_client = docker.from_env()

        platform = (
            experiment.env.remote_platform_arch
            if experiment.colocated_workload
            else experiment.env.remote_platform_arch
        )

        print(f"Building workload for platform {platform}")

        build = subprocess.check_call(
            [
                "docker",
                "buildx",
                "build",
                "--platform",
                platform,
                "-t",
                f"{experiment.env.docker_registry_address}/loadgenerator",
                ".",
            ],
            cwd=path.join("clue-loadgenerator", "teastore"),
        )
        if build != 0:
            raise RuntimeError("Failed to build loadgenerator")

        docker_client.images.push(f"{experiment.env.docker_registry_address}/loadgenerator")
        print(f"Built workload for platform {platform}")
        
def check_docker_laod_generator_image_exist(registry_address):
    docker_client = docker.from_env()
    try:
        docker_client.images.get_registry_data(f"{registry_address}/loadgenerator")
        return True
    except docker.errors.APIError:
        print(f"Loadgenerator not found in {registry_address} - rebuilding all images")
    return False

def switchBranch(sut_path, branch_name):
    git = subprocess.check_call(
            ["git", "switch", branch_name], cwd=path.join(sut_path)
        )
    if git != 0:
        raise RuntimeError(f"failed to switch git to {branch_name}")
        
    print(f"Using the {branch_name} branch")
    return branch_name

def build_main():
    # Read SUT_EXPERIMENT environment variable, use "all" for default
    exp_name = os.environ.get("SUT_EXPERIMENT", "all")
    
    # Get the experiment object
    experiment_list = ExperimentList.load_experiments(RUN_CONFIG)
    
    # If SUT_EXPERIMENT is "all" or unset, build all experiments
    if not exp_name or exp_name.lower() == "all":
        experiments = experiment_list
    else:
        # Look for the specified experiment
        selected_experiment = [e for e in experiment_list if e.name == exp_name]
        if selected_experiment:
            experiments = selected_experiment
        else:
            print(f"Experiment {exp_name} not found")
            sys.exit(1)  # Exit with error if experiment not found
    
    # Build the teastore images
    for experiment in experiments:
        print(f"Building teastore images for {experiment.name}")
        # Build the experiment
        #build(experiment)
        # Build the workload
        build_workload(experiment)

if __name__ == "__main__":
    build_main()