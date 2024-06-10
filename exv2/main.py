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

import experiment_list

DIRTY = True
SKIPBUILD = True


# setup clients
config.load_kube_config()
docker_client = docker.from_env()

# gloabls to drive the experiment





from csv import DictWriter


def build_images(exp: Experiment):
    """
    build all the images for the experiment and push them to the docker registry.

    perfrom some patching of the build scripts to use buildx (for multi-arch builds)
    """
    git = subprocess.check_call(
        ["git", "switch", exp.target_branch], cwd=path.join(env["tea_store_path"])
    )
    if git != 0:
        raise RuntimeError(f"failed to swich git to {exp.target_branch}")

    print(f"deploying {exp.target_branch}")

    # ensure mvn build ...
    # docker run -v foo:/mnt --rm -it --workdir /mnt  maven mvn clean install -DskipTests
    mvn = docker_client.containers.run(
        image="maven",
        auto_remove=True,
        volumes={
            path.abspath(path.join(env["tea_store_path"])): {
                "bind": "/mnt",
                "mode": "rw",
            }
        },
        working_dir="/mnt",
        command="mvn clean install -DskipTests",
        # command="tail -f /dev/null",
    )
    if "BUILD SUCCESS" not in mvn.decode("utf-8"):
        raise RuntimeError(
            "failed to build teastore. Run mvn clean install -DskipTests manually and see why it fails"
        )
    else:
        print("rebuild java deps")

    # patch build_docker.sh to use buildx
    with open(path.join(env["tea_store_path"], "tools", "build_docker.sh"), "r") as f:
        script = f.read()

    if "buildx" in script:
        print("buildx already used")
    else:
        script = script.replace(
            "docker build",
            f"docker buildx build --platform {env['remote_platform_arch']}",
        )
        with open(
            path.join(env["tea_store_path"], "tools", "build_docker.sh"), "w"
        ) as f:
            f.write(script)

    # 2. cd tools && ./build_docker.sh -r <env["docker_user"]/ -p && cd ..
    build = subprocess.check_call(
        ["sh", "build_docker.sh", "-r", f"{env['docker_user']}/", "-p"],
        cwd=path.join(env["tea_store_path"], "tools"),
    )

    if build != 0:
        raise RuntimeError(
            "failed to build docker images. Run build_docker.sh manually and see why it fails"
        )

    print(f"build {env['docker_user']}/* images")






def deploy_branch(exp: Experiment, observations: str = "data/default"):
    """
    deploy the helm chart with the given values.yaml,
    patching the values.yaml before deployment:
        - replace the docker user with the given user
        - replace the tag to ensure images are pulled
        - replace the node selector to ensure we only run on nodes that we can observe (require nodes to run scaphandre)
        - apply any patches given in the experiment (see yaml_patch)

    wait for the deployment to be ready, or timeout after 3 minutes
    """
    with open(
        path.join(env["tea_store_path"], "examples", "helm", "values.yaml"), "r"
    ) as f:
        values = f.read()
        values = values.replace("descartesresearch", env["docker_user"])
        # ensure we only run on nodes that we can observe
        values = values.replace(
            r"nodeSelector: {}", r'nodeSelector: {"scaphandre": "true"}'
        )
        values = values.replace("pullPolicy: IfNotPresent", "pullPolicy: Always")
        values = values.replace(r'tag: ""', r'tag: "latest"')
        if exp.autoscaling:
            values = values.replace(r"enabled: false", "enabled: true")
            # values = values.replace(r"clientside_loadbalancer: false",r"clientside_loadbalancer: true")
            if exp.autoscaling == ScalingExperimentSetting.MEMORYBOUND:
                values = values.replace(
                    r"targetCPUUtilizationPercentage: 80",
                    r"# targetCPUUtilizationPercentage: 80",
                )
                values = values.replace(
                    r"# targetMemoryUtilizationPercentage: 80",
                    r"targetMemoryUtilizationPercentage: 80",
                )
            elif exp.autoscaling == ScalingExperimentSetting.BOTH:
                values = values.replace(
                    r"# targetMemoryUtilizationPercentage: 80",
                    r"targetMemoryUtilizationPercentage: 80",
                )

    from yaml_patch import patch_yaml

    patch_yaml(values, exp.patches)

    with open(
        path.join(env["tea_store_path"], "examples", "helm", "values.yaml"), "w"
    ) as f:
        f.write(values)

    # write copy of used values to observations
    with open(path.join(observations, "values.yaml"), "w") as f:
        f.write(values)

    helm_deploy = subprocess.check_output(
        ["helm", "install", "teastore", "-n", exp.namespace, "."],
        cwd=path.join(env["tea_store_path"], "examples", "helm"),
    )
    helm_deploy = helm_deploy.decode("utf-8")
    if not "STATUS: deployed" in helm_deploy:
        raise RuntimeError(
            "failed to deploy helm chart. Run helm install manually and see why it fails"
        )

    wait_until_ready(
        ["teastore-auth", "teastore-registry", "teastore-webui"],
        180,
        namespace=exp.namespace,
    )

    if exp.autoscaling:
        setup_autoscaleing(exp)


def wait_until_ready(services, timeout, namespace="default"):

    v1 = client.AppsV1Api()
    ready_services = set()
    start_time = time.time()
    services = set(services)
    while len(ready_services) < len(services) and time.time() - start_time < timeout:
        for service in services.difference(
            ready_services
        ):  # only check services that are not ready yet
            try:
                service_status = v1.read_namespaced_stateful_set_status(
                    service, namespace
                )
                if (
                    service_status.status.ready_replicas
                    and service_status.status.ready_replicas > 0
                ):
                    ready_services.add(service)
            except Exception as e:
                print(e)
                pass
        if services == ready_services:
            return True
        time.sleep(1)
        print("waiting for deployment to be ready")
    raise RuntimeError(
        "Timeout reached. The following services are not ready: "
        + str(list(set(services) - set(ready_services)))
    )






def run_experiment(exp: Experiment, run: int, out: str = "data"):
    # 0. create experiment folder
    observations_out_path = path.join(out, exp.__str__(), f"{run}")

    try:
        try:
            os.makedirs(observations_out_path, exist_ok=DIRTY)
        except OSError:
            raise RuntimeError("data for this experiment already exsist, skipping")

        # 3. rewrite helm values with <env["docker_user"]> && env details as nessary (namespace ...)

        deploy_branch(exp, observations_out_path)

        # 4. run collection agent (fetch prometeus )
        if not DIRTY:
            time.sleep(120)  # wait for 120s before stressing the workload
        exp.run(observations_out_path)
    except RuntimeError as e:
        print(e)
    finally:
        cleanup(exp)


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
            build_images(exp)
        for i in range(experiment_list.NUM_ITERATIONS):
            out = "data"
            if exp.autoscaling:
                out += "_scale"
            if len(exp.env_patches) > 0:
                out += "_rampup"
            print(f"🏃‍♀️ running ({i+1}/{experiment_list.NUM_ITERATIONS})...")
            run_experiment(exp, i, out)



if __name__ == "__main__":
    main()