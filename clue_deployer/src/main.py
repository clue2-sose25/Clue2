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
from clue_deployer.config import Config
from clue_deployer.experiment import Experiment
from clue_deployer.experiment_runner import ExperimentRunner
from clue_deployer.experiment_workloads import get_workload_instance
from clue_deployer.experiment_list import ExperimentList
from clue_deployer.deploy import ExperimentDeployer

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("docker").setLevel(logging.INFO)
logging.getLogger("kubernetes").setLevel(logging.INFO)

logging.debug("debug log level")

# setup clients
config.load_kube_config()


def run_experiment(configs: Config, exp: Experiment, observations_out_path):
    # Create the experiment folder
    try:
        os.makedirs(observations_out_path, exist_ok=False)
    except OSError:
        raise RuntimeError("Data for this experiment already exist, skipping")
    print("🏗️ Deploying the SUT...")
    experiment_deployer = ExperimentDeployer(exp, configs)
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


def prepare_experiment(configs: Config, exp: Experiment, timestamp: str, num_iterations: int) -> None:
    
    print(f"ℹ️  New experiment: {exp}")

    for i in range(num_iterations):

        root = "data"
        name = exp.__str__()
        tags = "_".join(["exp"] + exp.env.tags)

        out_path = path.join(root, timestamp, tags, name, str(i))

        print(f"▶️ running ({i + 1}/{num_iterations}) to {out_path}...")
        run_experiment(configs, exp, out_path)
    
    print(f"Sleeping for 120s to let the system settle after one feature")
    time.sleep(120)

def main():
    # Read the environment variables
    sut = os.environ.get("SUT_NAME")
    exp_name = os.environ.get("EXPERIMENT_NAME", "all")
    base_dir_path = Path(__file__).resolve().parent.parent
    clue_config_path = base_dir_path.joinpath("clue-config.yaml")
    sut_path = f"/app/sut_configs/{sut}.yaml"
    configs = Config(sut_path, clue_config_path)
    
    # Load the experiments
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    exps = ExperimentList.load_experiments(configs, exp_name)
    
    # Get the workloads
    workloads = [get_workload_instance(w) for w in configs.clue_config.workloads]
    exps.add_workloads(workloads)

    # Sort the experiments
    exps.sort()
    print(tabulate([n.to_row() for n in exps], tablefmt="rounded_outline", headers=Experiment.headers()))
    progressbar.streams.wrap_stderr()

    # TODO: Print not working with pg2
    # for exp in progressbar.progressbar(exps, redirect_stdout=True, redirect_stderr=True):
    for exp in exps:
        prepare_experiment(configs, exp, timestamp, num_iterations=configs.sut_config.num_iterations)

if __name__ == "__main__":
    main()