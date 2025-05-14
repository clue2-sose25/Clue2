import os
from os import path
import sys
import docker
import subprocess
import yaml

# Add function to load YAML configs
def load_configs():
    # Load clue-config.yaml
    try:
        with open("clue-config.yaml", "r") as f:
            clue_config = yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: clue-config.yaml not found")
        sys.exit(1)
    
    # Load teastore.yaml
    try:
        with open("teastore.yaml", "r") as f:
            sut_config = yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: teastore.yaml not found")
        sys.exit(1)
        
    # Create a simple config object with the loaded data
    config = type('Config', (), {
        'clue_config': type('ClueConfig', (), clue_config)(),
        'sut_config': type('SutConfig', (), sut_config)()
    })()
    
    return config

# Global RUN_CONFIG
RUN_CONFIG = load_configs()

def build(experiment=None):
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
    
    branch_name = experiment.target_branch if experiment else RUN_CONFIG.sut_config.get('default_branch', 'master')
    switchBranch(teastore_path, branch_name)
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

def build_workload(experiment):
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

def switchBranch(sut_path, branch_name):
    git = subprocess.check_call(
            ["git", "switch", branch_name], cwd=path.join(sut_path)
        )
    if git != 0:
        raise RuntimeError(f"failed to switch git to {branch_name}")
        
    print(f"Using the {branch_name} branch")
    return branch_name

# Update the existing ExperimentList class to use configs
class ExperimentList:
    @staticmethod
    def load_experiments(run_config):
        # This is a placeholder for the actual experiment loading logic
        # You would replace this with your real experiment loading code
        experiments = []
        
        # Example of using config values
        try:
            # Get experiment definitions from config
            experiment_defs = run_config.clue_config.experiments
            for exp_def in experiment_defs:
                # Create experiment object with properties from config
                exp = type('Experiment', (), {
                    'name': exp_def.get('name'),
                    'target_branch': exp_def.get('target_branch', 'master'),
                    'colocated_workload': exp_def.get('colocated_workload', False),
                    'env': run_config.clue_config  # Pass the entire clue config as env
                })()
                experiments.append(exp)
        except (AttributeError, KeyError) as e:
            print(f"Error loading experiments from config: {e}")
            
        return experiments

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
        build(experiment)
        # Build the workload
        build_workload(experiment)

if __name__ == "__main__":
    build_main()