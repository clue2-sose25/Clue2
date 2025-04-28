#! /usr/bin/env python3
import copy
from datetime import datetime
import os
import time
from os import path
import sys
import progressbar
from kubernetes import config
from tabulate import tabulate
import argparse
import logging

import experiment_list
from experiment import Experiment
from experiment_deployer import ExperimentDeployer
from experiment_environment import ExperimentEnvironment, WorkloadAutoConfig
from experiment_runner import ExperimentRunner
from workload_runner import WorkloadRunner
from scaling_experiment_setting import ScalingExperimentSetting
from experiment_workloads import ShapredWorkload, RampingWorkload, PausingWorkload, FixedRampingWorkload



parser = argparse.ArgumentParser()
parser.add_argument("--skip-build" ,action="store_true",help="don't build, use latest image from registry")
parser.add_argument("--dirty" ,action="store_true",help="skip build, don't wait, and mix results")
parser.add_argument("--dry" ,action="store_true",help="just print exeriments")
args = parser.parse_args()

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("docker").setLevel(logging.INFO)
logging.getLogger("kubernetes").setLevel(logging.INFO)

logging.debug("debug log level")

DIRTY = args.dirty
SKIPBUILD = args.skip_build
DRY = args.dry

# setup clients
config.load_kube_config()


def full_run():
    exps = experiment_list.exps


    # foreach experiment, make a copy that uses rampup
    def set_workload(exp: Experiment, conf: WorkloadAutoConfig):
        new_ex = copy.deepcopy(exp)
        new_ex.env.set_workload(conf)
        return new_ex

    workloads = [
        ShapredWorkload(),
        # RampingWorkload(), 
        # PausingWorkload(),  
        # FixedRampingWorkload()
    ]

    exps = []
    for w in workloads:
        for exp in experiment_list.exps:
            exps.append(set_workload(exp,w))

    return exps

# def custom_reruns():
#     exps = []
#     prometheus_url = "http://130.149.158.130:32426"
#     namespace = "tea-bench"
#     scale = ScalingExperimentSetting.BOTH
    
#     e = Experiment(
#         name="baseline",
#         target_branch="vanilla",
#         # patches=[],
#         namespace=namespace,
#         colocated_workload=True,
#         prometheus_url=prometheus_url,
#         autoscaling=scale,
#     )
#     e.env.set_workload(ShapredWorkload())
#     exps.append(e)

#     return exps

def main():
    if DIRTY:
        print("☢️ will overwrite existing experiment data!!!!")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


    exps = full_run()
    # exps = custom_reruns()
    
    if DIRTY:
        for e in exps:
            e.env.tags.append("dirty")


    #sort by branch to speed up rebuilds ...
    def exp_sort_key(exp:Experiment):
        return "_".join([exp.target_branch,exp.name])

    exps.sort(key=exp_sort_key)
    
    print(tabulate([n.to_row() for n in exps], tablefmt="rounded_outline", headers=Experiment.headers()))

    if DRY:
        print("dry run -- exiting")
        return

    # master_env = copy.deepcopy(env)
    # todo
    progressbar.streams.wrap_stderr()
    # todo: print not working with pg2
    # for exp in progressbar.progressbar(exps, redirect_stdout=True, redirect_stderr=True):
    last_build_branch = None
    for exp in exps:
        print(f"ℹ️  new experiment: {exp}")
        if not SKIPBUILD:
            print("👷 building...")
            # if we know that branches don't change we could skip building some of them
            WorkloadRunner(exp).build_workload()
            if exp.target_branch != last_build_branch:
                ExperimentDeployer(exp).build_images()
            else:
                print(".. skipping build step, we've build the images for the last run already...")
            last_build_branch = exp.target_branch
        else:
            print("👷 skipping build...")

        for i in range(experiment_list.NUM_ITERATIONS):

            root = "data"
            name = exp.__str__()
            tags = "_".join(["exp"] + exp.env.tags)

            out_path = path.join(root, timestamp, tags, name, str(i))

            print(f"▶️ running ({i + 1}/{experiment_list.NUM_ITERATIONS}) to {out_path}...")
            run_experiment(exp, out_path)
        
        print(f"sleeping for 120s to let the system settle after one feature")
        time.sleep(120)


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
        print("error running experiment!")
        print(e)
    finally:
        ExperimentRunner(exp).cleanup()
        if not DIRTY:
            print(f"waiting {exp.env.wait_after_workloads}s after cleaning the workload")
            time.sleep(exp.env.wait_after_workloads)
    print("additional sleep after a run just to be on the safe side")
    time.sleep(60)


if __name__ == "__main__":
    main()
