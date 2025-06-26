import os
from os import path
import sys
import argparse
import re
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
    
    try:
        with open("sut_configs/teastore.yaml", "r") as f:
            sut_config = yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: teastore.yaml not found")
        sys.exit(1)
        
    # Create a simple config object with the loaded data
    config = type('Config', (), {
        'clue_config': type('ClueConfig', (), {
            'remote_platform_arch': clue_config['config']['remote_platform_arch'],
            'docker_registry_address': "registry:5000/clue"
        })(),
        'sut_config': type('SutConfig', (), {
            'sut_path': sut_config['config']['sut_path'],
            'experiments': sut_config.get('experiments', [])
        })()
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
    
    # Clone the sustainable_teastore 
    if not path.exists(sut_path):
        subprocess.check_call(["git", "clone", "https://github.com/ISE-TU-Berlin/sustainable_teastore.git", "teastore"])
        print("Cloned sustainable_teastore repository")
    
    branch_name = experiment.target_branch if experiment else RUN_CONFIG.sut_config.get('default_branch', 'master')
    switchBranch(sut_path, branch_name)
    run_maven(sut_path)
    patch_buildx(sut_path, remote_platform_arch, branch_name)
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

def patch_buildx(sut_path, remote_platform_arch, branch_name):
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

    # idempotent tagging: remove :whatever if present and append :branch_name
    script = re.sub(
        r'-t\s+"(\$\{registry\}[^:"]+)(?::[^"]*)?"',
        rf'-t "\1:{branch_name}"',
        script
    )

    # also for pushes
    script = re.sub(
        r'docker push\s+"(\$\{registry\}[^:"]+)(?::[^"]*)?"',
        rf'docker push "\1:{branch_name}"',
        script
    )

    with open(path.join(sut_path, "tools", "build_docker.sh"), "w") as f:
        f.write(script)

def run_maven(sut_path):
    print("Running Maven build directly for teastore. Might take a while...")
    
    try:
        # Print absolute path for debugging
        abs_path = path.abspath(sut_path)
        print(f"Using absolute path for Maven build: {abs_path}")
        
        # Check if the directory exists and has content
        if not path.exists(abs_path):
            print(f"Error: Path {abs_path} does not exist")
            sys.exit(1)
        else:
            print(f"Path exists. Contents: {os.listdir(abs_path)}")
        
        # Run Maven command directly
        process = subprocess.run(
            ["mvn", "clean", "install", "-DskipTests"],
            cwd=abs_path,
            capture_output=False,  # Capture stdout and stderr
            text=True  # Return output as strings instead of bytes
        )
        
        # Print Maven output for debugging
        print("Maven build output:")
        print(process.stdout)
        
        # Check the exit code
        if process.returncode != 0:
            print("Maven build failed with exit code:", process.returncode)
            print("Error logs:")
            print(process.stderr)
            raise RuntimeError(f"Failed to build teastore. Maven execution failed with exit code {process.returncode}")
        else:
            print("Finished rebuilding Java dependencies")
            
    except FileNotFoundError as e:
        print(f"Error: Maven is not installed or not found in PATH: {e}")
        raise RuntimeError("Maven is not installed or not found in PATH. Please install Maven and try again.")
    except Exception as e:
        print(f"Unexpected error during Maven build: {e}")
        raise

def build_workload(experiment):
        platform = (
            experiment.env.remote_platform_arch
            if experiment.colocated_workload
            else experiment.env.remote_platform_arch
        )
        registry = experiment.env.docker_registry_address
        branch = experiment.target_branch

        print(f"Building Teastore workload generator for platform {platform}")
        tag = f"{registry}/loadgenerator:{branch}"
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
            cwd=path.join("workload_generator"),
        )
        if build != 0:
            raise RuntimeError("Failed to build the workload generator")

        print(f"Built workload generator for platform {platform} and pushed to {tag}")

def switchBranch(sut_path, branch_name):
    git = subprocess.check_call(
            ["git", "switch", branch_name], cwd=path.join(sut_path)
        )
    if git != 0:
        raise RuntimeError(f"failed to switch git to {branch_name}")
        
    print(f"Using the {branch_name} branch")
    return branch_name

def build_main():
    # Read BUILDER_VARIANTS environment variable, use "all" for default
    exp_name = os.environ.get("TEASTORE_EXP_NAME", "all").lower().strip()
    
    # Allow multiple experiments per comma: ‘baseline,serverless’
    exp_list = [e.strip() for e in exp_name.split(",") if e.strip()]

    print(f"Starting Teastore Builder for experiment: {exp_name}")
    
    # Get the experiments directly from the config
    all_experiments = RUN_CONFIG.sut_config.experiments
    
    # Convert experiment dicts to simple objects for compatibility with the rest of the code
    experiments = []
    for exp_dict in all_experiments:
        exp = type('Experiment', (), {
            'name': exp_dict.get('name'),
            'target_branch': exp_dict.get('target_branch', 'master'),
            'colocated_workload': exp_dict.get('colocated_workload', False),
            'env': type('Env', (), {
                'remote_platform_arch': RUN_CONFIG.clue_config.remote_platform_arch,
                'docker_registry_address': "registry:5000/clue"
            })()
        })()
        experiments.append(exp)
    
    # If TEASTORE_EXP_NAME is "all" or unset, build all experiments
    if "all" in exp_list:
        selected_experiments = experiments
    else:
        # Look for the specified experiment
        selected_experiments = [e for e in experiments if e.name.lower() in exp_list]
        if not selected_experiments:
            print(f"No experiment found for: {exp_list}")
            sys.exit(1)  # Exit with error if experiment not found
    # Build the workload generator
    build_workload(selected_experiments[0])
    # Build the teastore images
    for experiment in selected_experiments:
        print(f"Building teastore images for {experiment.name}")
        # Build each experiment
        build(experiment)

if __name__ == "__main__":
    build_main()
