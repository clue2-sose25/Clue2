#! /usr/bin/env python3
import click
from click import echo
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

@click.group()
def cli():
    pass

# @click.command("list")
# def echo_experiments():
#     """List available Experiments"""
#     echo("\n".join([e.name for e in experiment_list.exps]))

def available_experiments():
    return [e.name for e in experiment_list.exps]


@click.command("run")
@click.argument("exp-name", type=click.Choice(available_experiments())) # default="baseline")
@click.option("--skip-build/--force-build", default=False)
@click.option("--kind", default=None)
@click.option("--platform", default="linux/amd64")
# @click.option("--service_name", default="teastore-webui")
# @click.option("--port", default="8080")
def run(exp_name: str, skip_build, kind, platform):
    """Build and run a given experiment's setup"""

    matching_exps = [e for e in experiment_list.exps if e.name == exp_name]

    if not len(matching_exps):
        # echo(f"unknown experiment f{exp_name}, choose one of:")
        # echo_experiments()
        # return -1
        raise ValueError("invalid experiment name")
    else:
        exp = matching_exps[0]

    echo(f"Experiment: {exp}")


    observations_out_path = "data_run/1"
    port_forward = None

    try:
        try:
            os.makedirs(observations_out_path, exist_ok=True)
        except OSError:
            raise RuntimeError("data for this experiment already exist, skipping")
        
        if kind:
            exp.env.kind_cluster_name = kind

        exp.env.remote_platform_arch = platform

        if not skip_build:
            echo("building images")
            ExperimentDeployer(exp).build_images()
        else:
            echo(click.style("skipping build", fg="green"))
        echo("🏗️ deploying branch")
        ExperimentDeployer(exp).deploy_branch(observations_out_path)

        echo("to expose port run:")
        echo(click.style("kubectl port-forward service/teastore-webui 8080:80", fg="cyan"))
        echo("")
        # v1 = kubernetes.client.AppsV1Api()
        # v1.list_name()


        # this does not work with kubernetes lib...
        #
        # echo(f"setting up port forward on {service_name} to {port}")
        # svc = kr8s.objects.Service.get(service_name)
        # echo(svc)
        # port_forward = svc.portforward(remote_port=port, local_port=80)
        # port_forward.start()  # Start the port forward in a background thread
        # ...
        #         # if port_forward:
        #     port_forward.stop() 


        # Your other code goes here

        click.pause()
        
        echo("shutting down")

        # ExperimentRunner(exp).run(observations_out_path)
    except RuntimeError as e:
        echo(e)
    finally:
        ExperimentRunner(exp).cleanup()


# cli.add_command(run)
# cli.add_command(echo_experiments)

if __name__ == "__main__":
    run()
