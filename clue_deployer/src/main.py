#! /usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os
import time
from os import path
import progressbar
from kubernetes import config
from tabulate import tabulate
import argparse
import logging
from clue_deployer.config import Config
from clue_deployer.experiment import Experiment
from clue_deployer.experiment_environment import ExperimentEnvironment
from clue_deployer.experiment_runner import ExperimentRunner
from clue_deployer.experiment_workloads import get_workload_instance
from clue_deployer.experiment_list import ExperimentList
from clue_deployer.deploy import ExperimentDeployer

#get the root directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent
print(f"BASE_DIR: {BASE_DIR}")
#parse arguments
parser = argparse.ArgumentParser(description="Experiment Runner")
parser.add_argument(
    "--exp",
    action="store_true",
    help="Which experiment to run",
)
parser.add_argument(
    "--dirty",
    action="store_true",
    help="Skip building, don't wait, and mix results.",
)
parser.add_argument(
    "--dry",
    action="store_true",
    help="Just print experiments without running them.",
)
parser.add_argument(
    "--sut-path",
    "-s",
    type=Path,
    #default to the teastore.yaml in the parent directory
    default=(BASE_DIR / "sut_configs" / "teastore.yaml"), 
    help="Path to the System Under Test (SUT).",
)
args = parser.parse_args()


CLUE_CONFIG_PATH = BASE_DIR.joinpath("clue-config.yaml")
DIRTY = args.dirty
DRY = args.dry
SUT_PATH = args.sut_path 
CONFIG = Config(SUT_PATH, CLUE_CONFIG_PATH)

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("docker").setLevel(logging.INFO)
logging.getLogger("kubernetes").setLevel(logging.INFO)

logging.debug("debug log level")

# setup clients
config.load_kube_config()


def run_experiment(exp: Experiment, observations_out_path):
    # Create the experiment folder
    try:
        os.makedirs(observations_out_path, exist_ok=DIRTY)
    except OSError:
        raise RuntimeError("data for this experiment already exist, skipping")
    # Rewrite helm values with <env["docker_user"]> && env details as necessary (namespace ...)
    print("🏗️ Deploying the SUT...")
    experiment_deployer = ExperimentDeployer(exp, CONFIG)
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


def prepare_experiment(exp: Experiment, timestamp: str, num_iterations: int, last_build_branch = None) -> None:
    
    print(f"ℹ️  New experiment: {exp}")

    for i in range(num_iterations):

        root = "data"
        name = exp.__str__()
        tags = "_".join(["exp"] + exp.env.tags)

        out_path = path.join(root, timestamp, tags, name, str(i))

        print(f"▶️ running ({i + 1}/{num_iterations}) to {out_path}...")
        run_experiment(exp, out_path)
    
    print(f"sleeping for 120s to let the system settle after one feature")
    time.sleep(120)

def main():
    if DIRTY:
        print("☢️ will overwrite existing experiment data!!!!")

    # load configs
    

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    exps = ExperimentList.load_experiments(CONFIG)
    
    #Get Workloads
    workloads = [get_workload_instance(w) for w in CONFIG.clue_config.workloads]
    exps.add_workloads(workloads)
    
    if DIRTY:
        for e in exps:
            e.env.tags.append("dirty")

    #sort experiments
    exps.sort()
    
    print(tabulate([n.to_row() for n in exps], tablefmt="rounded_outline", headers=Experiment.headers()))

    if DRY:
        print("dry run -- exiting")
        return

  
    progressbar.streams.wrap_stderr()
    # todo: print not working with pg2
    # for exp in progressbar.progressbar(exps, redirect_stdout=True, redirect_stderr=True):
    for exp in exps:
        prepare_experiment(exp, timestamp, num_iterations=CONFIG.sut_config.num_iterations)

if __name__ == "__main__":
    main()