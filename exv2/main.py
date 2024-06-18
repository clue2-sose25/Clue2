#! /usr/bin/env python3
import copy
from datetime import datetime
import os
import time
from os import path

import progressbar
from kubernetes import config
from tabulate import tabulate

import experiment_list
from experiment import Experiment
from experiment_deployer import ExperimentDeployer
from experiment_environment import ExperimentEnvironment
from experiment_runner import ExperimentRunner
from workload_runner import WorkloadRunner

DIRTY = False
SKIPBUILD = False
DRY = False

# setup clients
config.load_kube_config()


def main():
    if DIRTY:
        print("☢️ will overwrite existing experiment data!!!!")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


    exps = experiment_list.exps

    # foreach experiment, make a copy that uses rampup
    def rampup_copy(exp: Experiment):
        new_ex = copy.deepcopy(exp)
        new_ex.env.set_rampup()
        return new_ex

    # exps += [rampup_copy(exp) for exp in exps]

    print(tabulate([n.to_row() for n in exps], tablefmt="rounded_outline", headers=Experiment.headers()))

    if DRY:
        print("dry run -- exiting")
        return

    # master_env = copy.deepcopy(env)
    # todo
    progressbar.streams.wrap_stderr()
    # todo: print not working with pg2
    # for exp in progressbar.progressbar(exps, redirect_stdout=True, redirect_stderr=True):
    for exp in exps:
        print(f"ℹ️ new experiment: {exp}")

        exp.autoscaling = experiment_list.scale

        if not SKIPBUILD:
            print("👷 building...")
            WorkloadRunner(exp).build_workload()
            ExperimentDeployer(exp).build_images()
        else:
            print("👷 skipping build...")

        for i in range(experiment_list.NUM_ITERATIONS):

            root = "data"
            name = exp.__str__()
            tags = "_".join(["exp"] + exp.env.tags)

            out_path = path.join(root, timestamp, tags, name, str(i))

            print(f"▶️ running ({i + 1}/{experiment_list.NUM_ITERATIONS}) to {out_path}...")
            run_experiment(exp, out_path)


def run_experiment(exp: Experiment, observations_out_path):
    # 0. create experiment folder

    # new format: data/timestamp/scale/branch/i/files

    try:
        try:
            os.makedirs(observations_out_path, exist_ok=DIRTY)
        except OSError:
            raise RuntimeError("data for this experiment already exist, skipping")

        # 3. rewrite helm values with <env["docker_user"]> && env details as necessary (namespace ...)
        print("🏗️ deploying branch")
        ExperimentDeployer(exp).deploy_branch(observations_out_path)

        # 4. run collection agent (fetch prometheus )
        if not DIRTY:
            wait = ExperimentEnvironment().wait_before_workloads
            print(f"😴 waiting {wait}s before starting workload")
            time.sleep(wait)  # wait for 120s before stressing the workload

        ExperimentRunner(exp).run(observations_out_path)
    except RuntimeError as e:
        print(e)
    finally:
        ExperimentRunner(exp).cleanup()


if __name__ == "__main__":
    main()
