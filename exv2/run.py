#! /usr/bin/env python3
import click
from click import echo
from pathlib import Path
import os
from kubernetes import config

from experiment_list import ExperimentList
from experiment_deployer import ExperimentDeployer
from experiment_runner import ExperimentRunner

from config import Config

# setup clients
config.load_kube_config()

#get the root directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent
print(f"BASE_DIR: {BASE_DIR}")
CONFIG_PATH = BASE_DIR.joinpath("clue-config.yaml")
SUT_CONFIG_PATH = BASE_DIR / "sut_configs" / "teastore-config.yaml"
RUN_CONFIG = Config(SUT_CONFIG_PATH, CONFIG_PATH)


@click.group()
def cli():
    pass

# @click.command("list")
# def echo_experiments():
#     """List available Experiments"""
#     echo("\n".join([e.name for e in experiment_list.exps]))


def available_experiments():
    experiments= ExperimentList.load_experiments(RUN_CONFIG)
    return [e.name for e in experiments]


@click.command("run")
@click.argument("exp-name", type=click.Choice(available_experiments())) # default="baseline")
@click.option("--skip-build/--force-build", default=False)
@click.option("--kind", default=None)
@click.option("--platform", default="linux/amd64")
# @click.option("--service_name", default="teastore-webui")
# @click.option("--port", default="8080")
def run(exp_name: str, skip_build, kind, platform):
    """Build and run a given experiment's setup"""

    matching_exps = [e for e in ExperimentList.load_experiments(RUN_CONFIG) if e.name == exp_name]

    if not len(matching_exps):
        # echo(f"unknown experiment f{exp_name}, choose one of:")
        # echo_experiments()
        # return -1
        raise ValueError("invalid experiment name")
    else:
        exp = matching_exps[0]

    echo(f"Running the experiment: {exp}")

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
            echo("Building the SUT images")
            ExperimentDeployer(exp).build_images()
        else:
            echo(click.style("Skipping the SUT build.", fg="green"))
        echo("🏗️ Deploying the SUT")
        ExperimentDeployer(exp).deploy_branch(observations_out_path)

        echo("To expose port run:")
        echo(click.style("kubectl port-forward service/teastore-webui 8080:80 -n tea-bench", fg="cyan"))
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
