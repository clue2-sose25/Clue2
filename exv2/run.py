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
import kubernetes

import experiment_list
from experiment import Experiment
from experiment_deployer import ExperimentDeployer
from experiment_environment import ExperimentEnvironment, WorkloadAutoConfig
from experiment_runner import ExperimentRunner
from workload_runner import WorkloadRunner
from scaling_experiment_setting import ScalingExperimentSetting
from experiment_workloads import ShapredWorkload, RampingWorkload, PausingWorkload, FixedRampingWorkload


# setup clients
config.load_kube_config()



def main():
    exp = experiment_list.exps[0]
    print("Experiment:", exp)

    observations_out_path = "data_run/1"

    try:
        try:
            os.makedirs(observations_out_path, exist_ok=True)
        except OSError:
            raise RuntimeError("data for this experiment already exist, skipping")


        print("building images")
        ExperimentDeployer(exp).build_images()

        print("🏗️ deploying branch")
        ExperimentDeployer(exp).deploy_branch(observations_out_path)

        print("will run until keypress...")
        print("to expose port run:")
        print("kubectl port-forward service/teastore-webui 8080:80")
        print("")
        # v1 = kubernetes.client.AppsV1Api()
        # v1.list_name()
        input()
        print("shutting down")

        # ExperimentRunner(exp).run(observations_out_path)
    except RuntimeError as e:
        print(e)
    finally:
        ExperimentRunner(exp).cleanup()




if __name__ == "__main__":
    main()
