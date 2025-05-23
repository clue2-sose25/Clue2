#! /usr/bin/env python3
import os
from clue_deployer.deploy import ExperimentDeployer
from pathlib import Path
from clue_deployer.experiment_list import ExperimentList
from config import Config

#get the root directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR.joinpath("clue-config.yaml")
SUT_NAME = os.environ.get("SUT_NAME")
EXP_NAME = os.environ.get("EXPERIMENT_NAME")
SUT_CONFIG_PATH = BASE_DIR / "sut_configs" / f"{SUT_NAME}.yaml"
RUN_CONFIG = Config(SUT_CONFIG_PATH, CONFIG_PATH)


def available_suts():
    """
    Reads the 'sut_configs' folder and returns a list of available SUT names.
    """
    sut_configs_path = BASE_DIR / "sut_configs"
    if not sut_configs_path.exists():
        raise FileNotFoundError(f"SUT configs folder not found: {sut_configs_path}")

    # Get all YAML files in the 'sut_configs' folder
    sut_files = [f.stem for f in sut_configs_path.glob("*.yaml")]
    return sut_files


def run():
    # TODO: choose the correct sut_config and check if the experiment is available for the selected sut

    # Get the experiment object
    experiment_list = ExperimentList.load_experiments(RUN_CONFIG)
    experiments = [e for e in experiment_list if e.name == EXP_NAME]
    if not len(experiments):
        raise ValueError("invalid experiment name- the following are the available experiments for teastore: " + str([e.name for e in experiment_list]))
    else:   
        experiment = experiments[0]
        
    # Deploy the experiment, without the workload generator
    deployer = ExperimentDeployer(experiment, RUN_CONFIG)
    deployer.execute_deployment()

if __name__ == "__main__":
    run()
