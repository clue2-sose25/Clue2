#! /usr/bin/env python3
import click
from click import echo
from pathlib import Path
from kubernetes import config

from experiment_list import ExperimentList
from experiment_runner import ExperimentRunner

from config import Config

#get the root directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR.joinpath("clue-config.yaml")
SUT_CONFIG_PATH = BASE_DIR / "sut_configs" / "teastore-config.yaml"
RUN_CONFIG = Config(SUT_CONFIG_PATH, CONFIG_PATH)

@click.group()
def cli():
    pass

def available_suts():
    return ["teastore"]


@click.command("run")
@click.option("--sut", required=True, type=click.Choice(available_suts()))
@click.option("--exp-name", required=True, type=click.STRING, help="Name of the experiment to run")
@click.option("--force-build", default=False)
@click.option("--force-build-loadgenerator", default=False)
def run(sut: str, exp_name: str, force_build, force_build_loadgenerator):
    if sut == "teastore":
        testore_experiment(exp_name, force_build, force_build_loadgenerator)

def testore_experiment(exp_name, force_build, force_build_loadgenerator):
    from config.experiment_configs import SingleExperiment
    from builder.teastore import build
    from deployer.teastore import deploy
    # check if the experiment is in the list
    experiment_list = ExperimentList.load_experiments(RUN_CONFIG)
    experiments = [e for e in experiment_list if e.name == exp_name]
    if not len(experiments):
        raise ValueError("invalid experiment name- the following are the available experiments for teastore: " + str([e.name for e in experiment_list]))
    else:   
        experiment = experiments[0]
        
    if force_build or not build.check_docker_all_images_exist(RUN_CONFIG.clue_config.docker_registry_address):
        echo("Building docker images...")
        build.build(experiment)
    else:
        echo("Docker images are already built, skipping build step. You can use --force-build to force build the images.")
        
    if force_build_loadgenerator or not build.check_docker_laod_generator_image_exist(RUN_CONFIG.clue_config.docker_registry_address):
        echo("Building loadgenerator image...")
        build.build_workload(experiment)
    else:
        echo("Loadgenerator Docker image is already built, skipping build step. You can use --force-build-loadgenerator to force build the image.")
    
    # deploy the experiment
    deploy.deploy(experiment)

if __name__ == "__main__":
    run()
