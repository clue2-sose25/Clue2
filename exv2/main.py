#! /usr/bin/env python3
from enum import Enum
from queue import Queue, Empty
import os
from os import path
import math
import subprocess
import tarfile
from tempfile import TemporaryFile
import docker
import copy


from kubernetes import client, config, watch
from kubernetes.stream import stream
from kubernetes.client.rest import ApiException

import time
import signal
import base64
from requests import get

from experiment import Experiment
from scaling_experiment_setting import ScalingExperimentSetting
from workload_runner import WorkloadRunner
from experiment_environment import ExperimentEnvironment
from experiment_deployer import ExperimentDeployer

import experiment_list

DIRTY = True
SKIPBUILD = True


# setup clients
config.load_kube_config()


def main():
    if DIRTY:
        print("☢️ will overwrite existing experiment data!!!!")

    lin_workload = {
        "workload": {
            "LOCUSTFILE": "./locustfile.py",
            "RUN_TIME": f'{env["workload"]["LOADGENERATOR_STAGE_DURATION"]*8}s',
            "SPAWN_RATE": 3,
            "USERS": env["workload"]["LOADGENERATOR_MAX_DAILY_USERS"],
        }
    }

    # prometheus_url = "http://130.149.158.143:30041"
    nexps = []

    for exp in experiment_list.exps:
        # test differnt workload generator (ramp up stress)
        nexp = copy.deepcopy(exp)
        nexp.env_patches = lin_workload
        nexps.append(nexp)

    exps += nexps

    master_env = copy.deepcopy(env)
    for exp in exps:
        env = copy.deepcopy(master_env)
        for k, v in exp.env_patches.items():
            if k in env and isinstance(env[k], dict):
                for kk, vv in v.items():
                    env[k][kk] = vv
            else:
                env[k] = v

        print("ℹ️ new experiment:")
        print(exp)

        exp.autoscaling = experiment_list.scale

        if not SKIPBUILD:
            print("👷 building...")
            WorkloadRunner(exp).build_workload()
            ExperimentDeployer(exp).build_images()

        for i in range(experiment_list.NUM_ITERATIONS):
            out = "data"
            if exp.autoscaling:
                out += "_scale"
            if len(exp.env_patches) > 0:
                out += "_rampup"
            print(f"🏃‍♀️ running ({i+1}/{experiment_list.NUM_ITERATIONS})...")
            run_experiment(exp, i, out)


def run_experiment(exp: Experiment, iteration: int, out: str = "data"):
    # 0. create experiment folder
    observations_out_path = path.join(out, exp.__str__(), f"{iteration}")

    try:
        try:
            os.makedirs(observations_out_path, exist_ok=DIRTY)
        except OSError:
            raise RuntimeError("data for this experiment already exsist, skipping")

        # 3. rewrite helm values with <env["docker_user"]> && env details as nessary (namespace ...)
        ExperimentDeployer(exp).deploy_branch(observations_out_path)

        # 4. run collection agent (fetch prometeus )
        if not DIRTY:
            wait = ExperimentEnvironment().wait_before_workloads
            print(f"😴 waiting {wait}s before starting workload")
            time.sleep(wait)  # wait for 120s before stressing the workload
        exp.run(observations_out_path)
    except RuntimeError as e:
        print(e)
    finally:
        exp.cleanup()


if __name__ == "__main__":
    main()
