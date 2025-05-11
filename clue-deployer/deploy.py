import sys
from pathlib import Path
from os import path
from kubernetes.client import CoreV1Api, V1Namespace, V1ObjectMeta
from kubernetes.client.exceptions import ApiException
from kubernetes.client import AppsV1Api
import time
import os
import subprocess
from kubernetes import config

BASE_DIR = Path(__file__).resolve().parent.parent

from experiment import Experiment
from scaling_experiment_setting import ScalingExperimentSetting
from config import Config
from autoscaling_deployer import AutoscalingDeployer

CONFIG_PATH = BASE_DIR.joinpath("clue-config.yaml")
SUT_CONFIG_PATH = BASE_DIR / "sut_configs" / "teastore.yaml"
RUN_CONFIG = Config(SUT_CONFIG_PATH, CONFIG_PATH)

def deploy(experiment: Experiment):
    sut_path = RUN_CONFIG.sut_config.sut_path
    docker_registry_address = RUN_CONFIG.clue_config.docker_registry_address
    
    try:
        config.load_kube_config()
    except Exception as e:
        print("Failed to load kube config. Make sure you have a cluster available via kubectl.")
        raise e

    create_namespace_if_not_exists(experiment.namespace)
    check_labeled_node_available()
    ensure_helm_requirements()
    start_port_forward(experiment.namespace,"prometheus-kps1-kube-prometheus-stack-prometheus-0",9090,9090)
    patch_helm_deployment_for_experiment(experiment, sut_path, docker_registry_address)
    deploy_helm_chart(experiment, sut_path)
    wait_until_services_ready(experiment)

    if experiment.autoscaling:
        print("Autoscaling is enabled. Deploying autoscaling...")
        AutoscalingDeployer(experiment).setup_autoscaling()
    
    print("Deployment complete. You can now run the experiment.")
    
def wait_until_services_ready(experiment: Experiment, timeout: int = 180):
    v1_apps = AppsV1Api()
    ready_services = set()
    start_time = time.time()
    services = set(experiment.critical_services)
    namespace = experiment.namespace
    print("Waiting for deployment to be ready...")

    while len(ready_services) < len(services) and time.time() - start_time < timeout:
        for service in services.difference(ready_services):
            try:
                # Check StatefulSet status
                statefulset_status = v1_apps.read_namespaced_stateful_set_status(service, namespace)
                if statefulset_status.status.ready_replicas and statefulset_status.status.ready_replicas > 0:
                    ready_services.add(service)
                    continue

                # Check Deployment status
                deployment_status = v1_apps.read_namespaced_deployment_status(service, namespace)
                if deployment_status.status.ready_replicas and deployment_status.status.ready_replicas > 0:
                    ready_services.add(service)
            except ApiException as e:
                if e.status != 404:  # Ignore not found errors
                    print(f"Error checking status for service '{service}': {e}")
        if services == ready_services:
            print("All services are up!")
            return True
        time.sleep(1)

    raise RuntimeError("Timeout reached. The following services are not ready: " + str(list(services - ready_services)))

def deploy_helm_chart(experiment: Experiment, sut_path: str):
    try:
        helm_deploy = subprocess.check_output(
            ["helm", "install", "teastore", "-n", experiment.namespace, "."],
            cwd=path.join(sut_path, "examples", "helm"),
        )
        helm_deploy = helm_deploy.decode("utf-8")
        if not "STATUS: deployed" in helm_deploy:
            print(helm_deploy)
            raise RuntimeError("failed to deploy helm chart. Run helm install manually and see why it fails")
    except subprocess.CalledProcessError as cpe:
        print(cpe)
    

def patch_helm_deployment_for_experiment(experiment: Experiment, sut_path: str, docker_image_location: str):
    with open(path.join(sut_path, "examples", "helm", "values.yaml"), "r") as f:
        values = f.read()
        values = values.replace("descartesresearch", docker_image_location)
        # ensure we only run on nodes that we can observe - set nodeSelector to scaphandre
        values = values.replace(
            r"nodeSelector: {}", r'nodeSelector: {"scaphandre": "true"}'
        )
        values = values.replace("pullPolicy: IfNotPresent", "pullPolicy: Always")
        values = values.replace(r'tag: ""', r'tag: "latest"')
        if experiment.autoscaling:
            values = values.replace(r"enabled: false", "enabled: true")
            # values = values.replace(r"clientside_loadbalancer: false",r"clientside_loadbalancer: true")
            if experiment.autoscaling == ScalingExperimentSetting.MEMORYBOUND:
                values = values.replace(
                    r"targetCPUUtilizationPercentage: 80",
                    r"# targetCPUUtilizationPercentage: 80",
                )
                values = values.replace(
                    r"# targetMemoryUtilizationPercentage: 80",
                    r"targetMemoryUtilizationPercentage: 80",
                )
            elif experiment.autoscaling == ScalingExperimentSetting.BOTH:
                values = values.replace(
                    r"targetMemoryUtilizationPercentage: 80",
                    r"targetMemoryUtilizationPercentage: 80",
                )
    with open(path.join(sut_path, "examples", "helm", "values.yaml"), "w") as f:
        f.write(values)
    
    # create observations directory in the format RUN_CONFIG.clue_config.result_base_path / experiment.name / dd.mm.yyyy_hh:mm
    observations = path.join(RUN_CONFIG.clue_config.result_base_path, experiment.name, time.strftime("%d.%m.%Y_%H:%M"))
    os.makedirs(observations)

    # write copy of used values to observations 
    with open(path.join(observations, "values.yaml"), "w") as f:
        f.write(values)

def create_namespace_if_not_exists(namespace: str):
    v1 = CoreV1Api()
    try:
        v1.read_namespace(name=namespace)
        print(f"Namespace '{namespace}' already exists.")
    except ApiException as e:
        if e.status == 404:  # Namespace not found
            print(f"Namespace '{namespace}' does not exist. Creating it...")
            namespace_body = V1Namespace(metadata=V1ObjectMeta(name=namespace))
            v1.create_namespace(body=namespace_body)
            print(f"Namespace '{namespace}' created successfully.")
        else:
            raise  # Re-raise other exceptions
        
def check_labeled_node_available():
    v1 = CoreV1Api()
    nodes = v1.list_node(label_selector="scaphandre=true")
    if not nodes.items:
        raise RuntimeError("No nodes with label 'scaphandre=true' found. Please label a node and try again.")
    print(f"Found {len(nodes.items)} nodes with label 'scaphandre=true'.")

def ensure_helm_requirements():
    try:
        # Check if the prometheus-community repository is added
        helm_repos = subprocess.check_output(["helm", "repo", "list"], text=True)
        if "prometheus-community" not in helm_repos:
            print("Helm repository 'prometheus-community' is not added. Adding it now...")
            subprocess.check_call(["helm", "repo", "add", "prometheus-community", "https://prometheus-community.github.io/helm-charts"])
        if "kepler" not in helm_repos:
            print("Helm repository 'kepler' is not added. Adding it now...")
            subprocess.check_call(["helm", "repo", "add", "kepler", "https://sustainable-computing-io.github.io/kepler-helm-chart"])

        # Check if kube-prometheus-stack is installed
        prometheus_status = subprocess.run(
            ["helm", "status", "kps1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if prometheus_status.returncode != 0:
            print("Helm chart 'kube-prometheus-stack' is not installed. Installing it now...")
            subprocess.check_call(["helm", "install", "kps1", "prometheus-community/kube-prometheus-stack"])

        # Check if kepler is installed
        kepler_status = subprocess.run(
            ["helm", "status", "kepler", "--namespace", "kepler"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if kepler_status.returncode != 0:
            print("Helm chart 'kepler' is not installed. Installing it now...")
            subprocess.check_call([
                "helm", "install", "kepler", "kepler/kepler",
                "--namespace", "kepler",
                "--create-namespace",
                "--set", "serviceMonitor.enabled=true",
                "--set", "serviceMonitor.labels.release=kps1"
            ])
        print("All Helm requirements are fulfilled.")
    except subprocess.CalledProcessError as e:
        print(f"Error while fulfilling Helm requirements: {e}")
        raise RuntimeError("Failed to fulfill Helm requirements. Please check the error above.")
    
def start_port_forward(namespace: str, pod_name: str, local_port: int, remote_port: int):
    try:
        print(f"Starting port-forward: {local_port} -> {pod_name}:{remote_port} in namespace '{namespace}'")
        process = subprocess.Popen(
            [
                "kubectl", "--namespace", namespace, "port-forward",
                pod_name, f"{local_port}:{remote_port}"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print(f"Port-forward started successfully. PID: {process.pid}")
        return process
    except Exception as e:
        print(f"Failed to start port-forward: {e}")
        raise RuntimeError("Failed to start port-forward. Please check the error above.")