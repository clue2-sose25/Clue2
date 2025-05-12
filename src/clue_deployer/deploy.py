from pathlib import Path
from os import path
from kubernetes.client import CoreV1Api, V1Namespace, V1ObjectMeta, AppsV1Api
from kubernetes.client.exceptions import ApiException
import time
import os
import subprocess
from kubernetes import config as k_config

# Assuming these are correctly imported from your project structure
from clue_deployer.experiment import Experiment
from clue_deployer.scaling_experiment_setting import ScalingExperimentSetting 
from config import Config # Assuming this is your main combined config object
from clue_deployer.autoscaling_deployer import AutoscalingDeployer

# BASE_DIR and other global constants might be better managed within the Config object
# or passed to the ExperimentDeployer if they vary. For now, assuming they are accessible.
BASE_DIR = Path(__file__).resolve().parent.parent.parent # Adjust if deploy.py is not 3 levels down from project root
# CONFIG_PATH = BASE_DIR.joinpath("clue-config.yaml") # Likely part of the 'Config' object now
# SUT_CONFIG_PATH = BASE_DIR / "sut_configs" / "teastore.yaml" # Likely part of the 'Config' object now


class ExperimentDeployer:
    def __init__(self, experiment: Experiment, config: Config):
        self.experiment = experiment
        self.config = config # This object should hold clue_config, sut_config, etc.

        # Extract paths and addresses from the config object
        # Ensure your Config class structure provides these attributes
        if not hasattr(config, 'sut_config') or not hasattr(config.sut_config, 'sut_path'):
            raise ValueError("Config object must have 'sut_config' with a 'sut_path' attribute.")
        self.sut_path = Path(config.sut_config.sut_path) # Ensure sut_path is a Path object

        if not hasattr(config, 'clue_config') or not hasattr(config.clue_config, 'docker_registry_address'):
            raise ValueError("Config object must have 'clue_config' with a 'docker_registry_address' attribute.")
        self.docker_registry_address = config.clue_config.docker_registry_address
        
        # Initialize Kubernetes API clients
        try:
            k_config.load_kube_config()
            self.core_v1_api = CoreV1Api()
            self.apps_v1_api = AppsV1Api()
        except Exception as e:
            print(f"Failed to load kube config: {e}. Make sure you have a cluster available via kubectl.")
            raise

        self.port_forward_process = None # To keep track of the port-forwarding process

    def _create_namespace_if_not_exists(self):
        namespace = self.experiment.namespace
        try:
            self.core_v1_api.read_namespace(name=namespace)
            print(f"Namespace '{namespace}' already exists.")
        except ApiException as e:
            if e.status == 404:  # Namespace not found
                print(f"Namespace '{namespace}' does not exist. Creating it...")
                namespace_body = V1Namespace(metadata=V1ObjectMeta(name=namespace))
                self.core_v1_api.create_namespace(body=namespace_body)
                print(f"Namespace '{namespace}' created successfully.")
            else:
                print(f"Error checking/creating namespace '{namespace}': {e}")
                raise

    def _check_labeled_node_available(self):
        label_selector = "scaphandre=true"
        try:
            nodes = self.core_v1_api.list_node(label_selector=label_selector)
            if not nodes.items:
                raise RuntimeError(f"No nodes with label '{label_selector}' found. Please label a node and try again.")
            print(f"Found {len(nodes.items)} nodes with label '{label_selector}'.")
        except ApiException as e:
            print(f"Error listing nodes with label '{label_selector}': {e}")
            raise

    def _ensure_helm_requirements(self):
        print("Ensuring Helm requirements (Prometheus, Kepler)...")
        try:
            
            # Check if the prometheus-community repository is added
            helm_repos = subprocess.check_output(["helm", "repo", "list"], text=True)
            if "prometheus-community" not in helm_repos:
                print("Helm repository 'prometheus-community' is not added. Adding it now...")
                subprocess.check_call(["helm", "repo", "add", "prometheus-community", "https://prometheus-community.github.io/helm-charts"])
            if "kepler" not in helm_repos:
                print("Helm repository 'kepler' is not added. Adding it now...")
                subprocess.check_call(["helm", "repo", "add", "kepler", "https://sustainable-computing-io.github.io/kepler-helm-chart"])

            # Update Helm repos
            subprocess.check_call(["helm", "repo", "update"])


           
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
    


    def _start_port_forward(self, pod_name_selector: str, local_port: int, remote_port: int):
        pod_name = pod_name_selector 
        namespace = self.experiment.namespace 

        if self.port_forward_process and self.port_forward_process.poll() is None:
            print(f"Port-forward process already running for {pod_name}.")
            return

        try:
            print(f"Starting port-forward: {local_port} -> {pod_name}:{remote_port} in namespace '{namespace}'")
            self.port_forward_process = subprocess.Popen(
                [
                    "kubectl", "--namespace", namespace, "port-forward",
                    pod_name, f"{local_port}:{remote_port}"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"Port-forward started successfully. PID: {self.port_forward_process.pid}")
            return self.port_forward_process
        except Exception as e:
            print(f"Failed to start port-forward: {e}")
            raise RuntimeError("Failed to start port-forward. Please check the error above.")


    def _patch_helm_deployment(self):
        with open(path.join(self.sut_path, "examples", "helm", "values.yaml"), "r") as f:
            values = f.read()
            values = values.replace("descartesresearch", self.config.clue_config.docker_registry_address)
            # ensure we only run on nodes that we can observe - set nodeSelector to scaphandre
            values = values.replace(
                r"nodeSelector: {}", r'nodeSelector: {"scaphandre": "true"}'
            )
            values = values.replace("pullPolicy: IfNotPresent", "pullPolicy: Always")
            values = values.replace(r'tag: ""', r'tag: "latest"')
            if self.experiment.autoscaling:
                values = values.replace(r"enabled: false", "enabled: true")
                # values = values.replace(r"clientside_loadbalancer: false",r"clientside_loadbalancer: true")
                if self.experiment.autoscaling == ScalingExperimentSetting.MEMORYBOUND:
                    values = values.replace(
                        r"targetCPUUtilizationPercentage: 80",
                        r"# targetCPUUtilizationPercentage: 80",
                    )
                    values = values.replace(
                        r"# targetMemoryUtilizationPercentage: 80",
                        r"targetMemoryUtilizationPercentage: 80",
                    )
                elif self.experiment.autoscaling == ScalingExperimentSetting.BOTH:
                    values = values.replace(
                        r"targetMemoryUtilizationPercentage: 80",
                        r"targetMemoryUtilizationPercentage: 80",
                    )
        with open(path.join(self.sut_path, "examples", "helm", "values.yaml"), "w") as f:
            f.write(values)
        
        # create observations directory in the format RUN_CONFIG.clue_config.result_base_path / experiment.name / dd.mm.yyyy_hh:mm
        observations = path.join(self.config.clue_config.result_base_path, self.experiment.name, time.strftime("%d.%m.%Y_%H:%M"))
        os.makedirs(observations)

        # write copy of used values to observations 
        with open(path.join(observations, "values.yaml"), "w") as f:
            f.write(values)

    def _deploy_helm_chart(self):
        try:
            helm_deploy = subprocess.check_output(
                ["helm", "install", "teastore", "-n", self.experiment.namespace, "."],
                cwd=path.join(self.sut_path, "examples", "helm"),
            )
            helm_deploy = helm_deploy.decode("utf-8")
            if not "STATUS: deployed" in helm_deploy:
                print(helm_deploy)
                raise RuntimeError("failed to deploy helm chart. Run helm install manually and see why it fails")
        except subprocess.CalledProcessError as cpe:
            print(cpe)

    def _wait_until_services_ready(self, timeout: int = 180):
        v1_apps = self.apps_v1_api
        ready_services = set()
        start_time = time.time()
        services = set(self.experiment.critical_services)
        namespace = self.experiment.namespace
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
    
    def _setup_autoscaling(self):
        print("Autoscaling is enabled. Deploying autoscaling...")
        # Pass necessary API clients to AutoscalingDeployer if it needs them
        autoscaler = AutoscalingDeployer(self.experiment, self.apps_v1_api, self.core_v1_api)
        autoscaler.setup_autoscaling()


    def execute_deployment(self):
        """
        Orchestrates the full deployment process for the experiment.
        """
        print(f"--- Starting Deployment for Experiment: {self.experiment.name} ---")
        self._create_namespace_if_not_exists()
        self._check_labeled_node_available() # Checks for "scaphandre=true"
        self._ensure_helm_requirements() # Installs Prometheus, Kepler

        # Determine Prometheus pod name for port-forwarding
        # This is a common pattern but might need adjustment based on actual prometheus deployment
        # For kube-prometheus-stack, the service is often more stable
        #TODO remove the hardcoding here
        self._start_port_forward("prometheus-kps1-kube-prometheus-stack-prometheus-0",9090,9090)
        self._patch_helm_deployment()
        self._deploy_helm_chart()
        self._wait_until_services_ready()
        
        if self.experiment.autoscaling:
            print("Autoscaling is enabled. Deploying autoscaling...")
            AutoscalingDeployer(self.experiment).setup_autoscaling()
    
        print("Deployment complete. You can now run the experiment.")