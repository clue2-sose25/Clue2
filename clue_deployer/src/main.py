from pathlib import Path
from datetime import datetime
import os
import time
from os import path
from typing import Optional
import progressbar
from kubernetes import config
from tabulate import tabulate
from clue_deployer.src.config.config import CONFIGS, ENV_CONFIG, Config
from logger import logger

import urllib3
from clue_deployer.service.status import Phase
from clue_deployer.service.status_manager import StatusManager
from clue_deployer.src.config.env_config import EnvConfig
from clue_deployer.src.experiment import Experiment
from clue_deployer.src.experiment_runner import ExperimentRunner
from clue_deployer.src.experiment_workloads import get_workload_instance
from clue_deployer.src.experiment_list import ExperimentList
from clue_deployer.src.deploy import ExperimentDeployer

# Load K8s config
config.load_kube_config()


def available_suts():
    """
    Reads the 'sut_configs' folder and returns a list of available SUT names.
    """
    if not ENV_CONFIG.SUT_CONFIGS_PATH.exists():
        logger.error(f"SUT configs folder not found: {ENV_CONFIG.SUT_CONFIGS_PATH}")
        raise FileNotFoundError(f"SUT configs folder not found: {ENV_CONFIG.SUT_CONFIGS_PATH}")
    # Get all YAML files in the 'sut_configs' folder
    sut_files = [f.stem for f in ENV_CONFIG.SUT_CONFIGS_PATH.glob("*.yaml")]
    return sut_files


def run_single_experiment(exp: Experiment, observations_out_path: Optional[Path] = None, config: Config = CONFIGS) -> None:
    """
    Executes and runs a single experiment
    """
    # Create the experiment folder if necessary
    if observations_out_path is not None:
        logger.info("Creating a results folder")
        try:
            os.makedirs(observations_out_path, exist_ok=False)
        except OSError:
            logger.warning("Data for this experiment already exist, skipping")
            raise RuntimeError("Data for this experiment already exist, skipping")
    else:
        logger.info("Skipping creating a results directory")
    logger.info("Deploying the SUT")
    # Deploy the SUT
    experiment_deployer = ExperimentDeployer(exp, config)
    experiment_deployer.deploy_SUT()
    # If not deploy only, run the benchmark
    if not ENV_CONFIG.DEPLOY_ONLY:
        logger.info("Starting the benchmark")
        # Wait for the SUT
        logger.info(f"Waiting {exp.env.wait_before_workloads}s before starting workload")
        time.sleep(exp.env.wait_before_workloads)  # wait for 120s before stressing the workload
        # Run the experiment
        ExperimentRunner(exp).run(observations_out_path)
        # Clean up
        logger.info("Cleaning up after the experiment")
        ExperimentRunner(exp).cleanup(experiment_deployer.helm_wrapper)
        logger.info(f"Waiting {exp.env.wait_after_workloads}s after cleaning the workload")
        time.sleep(exp.env.wait_after_workloads)
        logger.info("Waiting 60 sleep after a run just to be on the safe side")
        time.sleep(60)
        logger.info("All benchmarks executed successfully. Exiting CLUE.")
    else:
        logger.info("Deployment tested successfully. Exiting CLUE.")


def iterate_single_experiment(exp: Experiment, timestamp: str, num_iterations: int) -> None:
    """
    Iterates over the experiment
    """
    logger.info(f"Starting {exp} experiment")
    # Run all iterations
    for i in range(num_iterations):
        root = "data"
        name = exp.__str__()
        tags = "_".join(["exp"] + exp.env.tags)
        out_path = path.join(root, timestamp, tags, name, str(i))
        logger.info(f"Running iteration ({i + 1}/{num_iterations}) with output to: {out_path}")
        run_single_experiment(exp, out_path, CONFIGS)
    # Wait
    logger.info(f"Sleeping for 120s to let the system settle after one experiment")
    time.sleep(120)

def main() -> None:
    logger.info(f"Starting CLUE with DEPLOY_ONLY={ENV_CONFIG.DEPLOY_ONLY}")
    # Disable SSL verification
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    logger.info("Disabled SLL verification for urllib3")
    # Check if SUT_NAME is valid
    available_suts_list = available_suts()
    if ENV_CONFIG.SUT_NAME not in available_suts_list:
        logger.error(f"Invalid SUT name: '{ENV_CONFIG.SUT_NAME}'")
        logger.info(f"Available SUTs: {available_suts_list}")
        return
    # Load the experiments
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    exps = ExperimentList.load_experiments(CONFIGS, ENV_CONFIG.EXPERIMENT_NAME)
    logger.info(f"Loaded {len(exps.experiments)} experiments to run")
    # Check if the list is not empty
    if not len(exps.experiments):
        raise ValueError(f"Invalid experiment name for {ENV_CONFIG.SUT_NAME}")
    # Set the status to preparing
    StatusManager.set(Phase.PREPARING_CLUSTER, "Preparing the cluster...")
    # Deploy a single experiment if deploy only
    if ENV_CONFIG.DEPLOY_ONLY:
        logger.info(f"Starting experiment: {exps.experiments[0]}")
        run_single_experiment(exps.experiments[0])
    else:
        # Get the workloads
        logger.info("Appending workloads to the experiments")
        workloads = [get_workload_instance(w) for w in CONFIGS.clue_config.workloads]
        exps.add_workloads(workloads)
        # Sort and log the experiments
        exps.sort()
        logger.info("Running the following experiments:")
        i = 0
        for exp in exps.experiments:
            logger.info(f"Experiment no.{i}: {exp}")
            i = i + 1
        progressbar.streams.wrap_stderr()
        # Run over all iterations of each of the experiments
        for exp in exps:
            iterate_single_experiment(exp, timestamp, num_iterations=CONFIGS.sut_config.num_iterations)


if __name__ == "__main__":
    main()