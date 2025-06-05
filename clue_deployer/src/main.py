#! /usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os
import time
from os import path
import progressbar
from kubernetes import config
from tabulate import tabulate
import logging
import urllib3
from clue_deployer.src.config import Config, EnvConfig
from clue_deployer.src.experiment import Experiment
from clue_deployer.src.experiment_runner import ExperimentRunner
from clue_deployer.src.experiment_workloads import get_workload_instance
from clue_deployer.src.experiment_list import ExperimentList
from clue_deployer.src.deploy import ExperimentDeployer

# TODO: Implement secure connection
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_CONFIG = EnvConfig.get_env_config()
CLUE_CONFIG_PATH = ENV_CONFIG.CLUE_CONFIG_PATH
SUT_NAME = ENV_CONFIG.SUT_NAME
SUT_PATH = ENV_CONFIG.SUT_CONFIG_PATH
EXP_NAME = ENV_CONFIG.EXPERIMENT_NAME
CONFIG = Config()

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("docker").setLevel(logging.INFO)
logging.getLogger("kubernetes").setLevel(logging.INFO)

logging.debug("debug log level")

# setup clients
config.load_kube_config()


def run_experiment(exp: Experiment, observations_out_path: Path, config: Config = CONFIG) -> None:
    # Create the experiment folder
    try:
        os.makedirs(observations_out_path, exist_ok=False)
    except OSError:
        raise RuntimeError("Data for this experiment already exist, skipping")
    print("🏗️ Deploying the SUT...")
    experiment_deployer = ExperimentDeployer(exp, config)
    experiment_deployer.execute_deployment()
    # Wait for the SUT
    print(f"😴 Waiting {exp.env.wait_before_workloads}s before starting workload")
    time.sleep(exp.env.wait_before_workloads)  # wait for 120s before stressing the workload
    # Run the experiment
    ExperimentRunner(exp).run(observations_out_path)
    # Clean up
    ExperimentRunner(exp).cleanup(experiment_deployer.helm_wrapper)
    print(f"Waiting {exp.env.wait_after_workloads}s after cleaning the workload")
    time.sleep(exp.env.wait_after_workloads)
    print("Additional sleep after a run just to be on the safe side")
    time.sleep(60)


def prepare_experiment(exp: Experiment, timestamp: str, num_iterations: int, config: Config = CONFIG) -> None:
    
    print(f"ℹ️  New experiment: {exp}")

    for i in range(num_iterations):

        root = "data"
        name = exp.__str__()
        tags = "_".join(["exp"] + exp.env.tags)

        out_path = path.join(root, timestamp, tags, name, str(i))

        print(f"▶️ Running iteration ({i + 1}/{num_iterations}) with output to: {out_path}")
        run_experiment(exp, out_path, config)
    
    print(f"Sleeping for 120s to let the system settle after one feature")
    time.sleep(120)

def main(config: Config = CONFIG, exp_name: str = EXP_NAME) -> None:
    # Load the experiments
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    exps = ExperimentList.load_experiments(config, exp_name)
    
    # Get the workloads
    workloads = [get_workload_instance(w) for w in CONFIG.clue_config.workloads]
    exps.add_workloads(workloads)

    # Sort the experiments
    exps.sort()
    print(tabulate([n.to_row() for n in exps], tablefmt="rounded_outline", headers=Experiment.headers()))
    progressbar.streams.wrap_stderr()

    # TODO: Print not working with pg2
    # for exp in progressbar.progressbar(exps, redirect_stdout=True, redirect_stderr=True):
    for exp in exps:
        prepare_experiment(exp, timestamp, num_iterations=config.sut_config.num_iterations, config=config)

if __name__ == "__main__":
    main(CONFIG, EXP_NAME)