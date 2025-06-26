from pathlib import Path
from os import path
from kubernetes.client import CoreV1Api, V1Namespace, V1ObjectMeta, AppsV1Api
from kubernetes.client.exceptions import ApiException   
from clue_deployer.src.config.config import ENV_CONFIG
from clue_deployer.src.logger import logger
import time
import os
import subprocess
from kubernetes import config as k_config
from clue_deployer.src.helm_wrapper import HelmWrapper
from clue_deployer.src.models.experiment import Experiment
from clue_deployer.src.config import Config
from clue_deployer.src.autoscaling_deployer import AutoscalingDeployer
from clue_deployer.src.service.status_manager import StatusManager, StatusPhase

# Adjust if deploy.py is not 3 levels down from project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent 

class ExperimentDeployer:
    def __init__(self, experiment: Experiment, config: Config):
        self.experiment = experiment
        # This object should hold clue_config, sut_config, etc.
        self.config = config 

        # Extract paths and addresses from the config object
        # Ensure your Config class structure provides these attributes
        if not hasattr(config, 'sut_config') or not hasattr(config.sut_config, 'sut_path'):
            raise ValueError("Config object must have 'sut_config' with a 'sut_path' attribute.")
        self.sut_path = Path(config.sut_config.sut_path) # Ensure sut_path is a Path object

        if not hasattr(config, 'clue_config') or not hasattr(config.clue_config, 'docker_registry_address'):
            raise ValueError("Config object must have 'clue_config' with a 'docker_registry_address' attribute.")
        self.docker_registry_address = config.clue_config.docker_registry_address
        
        self.helm_chart_path = config.sut_config.helm_chart_path
        self.values_yaml_name = config.sut_config.values_yaml_name
        # Initialize Kubernetes API clients
        try:
            k_config.load_kube_config()
            self.core_v1_api = CoreV1Api()
            self.apps_v1_api = AppsV1Api()
        except Exception as e:
            logger.error(f"Failed to load kube config: {e}. Make sure you have a cluster available via kubectl.")
            raise

        self.port_forward_process = None # To keep track of the port-forwarding process
        self.helm_wrapper = HelmWrapper(self.config, self.experiment) 
    


    def _create_namespace_if_not_exists(self):
        """
        Checks if the given namespace exists in the cluster
        """
        namespace = self.experiment.namespace
        try:
            self.core_v1_api.read_namespace(name=namespace)
            logger.info(f"Namespace '{namespace}' already exists.")
        except ApiException as e:
            if e.status == 404:  # Namespace not found
                logger.info(f"Namespace '{namespace}' does not exist. Creating it...")
                namespace_body = V1Namespace(metadata=V1ObjectMeta(name=namespace))
                self.core_v1_api.create_namespace(body=namespace_body)
                logger.info(f"Namespace '{namespace}' created successfully.")
            else:
                logger.error(f"Error checking/creating namespace '{namespace}': {e}")
                raise

    def _check_labeled_node_available(self):
        """
        Checks if the cluster contains nodes with a label: scaphandre=true
        """
        label_selector = "scaphandre=true"
        try:
            nodes = self.core_v1_api.list_node(label_selector=label_selector)
            if not nodes.items:
                raise RuntimeError(f"No nodes with label '{label_selector}' found. Please label a node and try again.")
            logger.info(f"Found {len(nodes.items)} nodes with label '{label_selector}'.")
        except ApiException as e:
            logger.error(f"Error listing nodes with label '{label_selector}': {e}")
            raise 

    
    def _ensure_helm_requirements(self):
        """
        Checks if the cluster has deployed necessary observability tools, such as: Prometheus, Kepler
        """
        try:
            # Check if the prometheus-community repository is added
            try:
                helm_repos = subprocess.check_output(["helm", "repo", "list"], text=True)
            except subprocess.CalledProcessError:
                helm_repos = ""  # No repos yet
            if "prometheus-community" not in helm_repos:
                logger.info("Helm repository 'prometheus-community' is not added. Adding it now...")
                subprocess.check_call(["helm", "repo", "add", "prometheus-community", "https://prometheus-community.github.io/helm-charts"])
            if "kepler" not in helm_repos:
                logger.info("Helm repository 'kepler' is not added. Adding it now...")
                subprocess.check_call(["helm", "repo", "add", "kepler", "https://sustainable-computing-io.github.io/kepler-helm-chart"])
            # Update Helm repos
            logger.info("Updating helm repos")
            subprocess.check_call(["helm", "repo", "update"])
            # Check if kube-prometheus-stack is installed
            logger.info("Checking for Prometheus stack")
            prometheus_status = subprocess.run(
                ["helm", "status", "kps1"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
                )
            if prometheus_status.returncode != 0:
                logger.info("Helm chart 'kube-prometheus-stack' is not installed. Installing it now...")
                logger.info("Note: You may see some 'memcache.go' warnings during installation - these are harmless.")
                
                # Install with NodePort service type for Prometheus
                subprocess.check_call([
                    "helm", "install", "kps1", "prometheus-community/kube-prometheus-stack",
                    "--set", "prometheus.service.type=NodePort",
                    "--set", "prometheus.service.nodePort=30090",
                    "--wait",
                    "--timeout", "15m"
                ])
            else:
                logger.info("Prometheus stack found")
                # Check if service is already NodePort, if not patch it
                try:
                    service_info = subprocess.check_output([
                        "kubectl", "get", "svc", "kps1-kube-prometheus-stack-prometheus", 
                        "-o", "jsonpath={.spec.type}"
                    ], text=True)
                    
                    if service_info.strip() != "NodePort":
                        logger.info("Converting Prometheus service to NodePort...")
                        subprocess.check_call([
                            "kubectl", "patch", "svc", "kps1-kube-prometheus-stack-prometheus",
                            "-p", '{"spec":{"type":"NodePort","ports":[{"port":9090,"targetPort":9090,"nodePort":30090}]}}'
                        ])
                    else:
                        logger.info("Prometheus service is already NodePort")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Could not check/patch Prometheus service: {e}")

            # Check if kepler is installed
            logger.info("Checking for Kepler stack")
            kepler_status = subprocess.run(
                ["helm", "status", "kepler", "--namespace", "kepler"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if kepler_status.returncode != 0:
                logger.info("Helm chart 'Kepler' is not installed. Installing it now...")
                subprocess.check_call([
                    "helm", "install", "kepler", "kepler/kepler",
                    "--namespace", "kepler",
                    "--create-namespace",
                    "--set", "serviceMonitor.enabled=true",
                    "--set", "serviceMonitor.labels.release=kps1",
                    "--wait",
                    "--timeout", "10m"
                ])
            else:
                logger.info("Kepler stack found")
            logger.info("All cluster requirements fulfilled")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error while fulfilling Helm requirements: {e}")
            raise RuntimeError("Failed to fulfill Helm requirements. Please check the error above.")
            

    def _creates_results_directory(self, values: dict):
        # Create observations directory in the format RUN_CONFIG.clue_config.result_base_path / experiment.name / dd.mm.yyyy_hh-mm
        observations = path.join("/data", self.experiment.name, time.strftime("%d.%m.%Y_%H-%M"))
        os.makedirs(observations)
        # Write copy of used values to observations 
        with open(path.join(observations, "values.yaml"), "w") as f:
            f.write(values)
            logger.info("Copying values file to results")


    def _wait_until_services_ready(self):
        """
        Wait a specified amount of time for the critical services
        """
        timeout = self.config.sut_config.timeout_for_services_ready
        logger.info(f"Waiting for critical services to be ready for {timeout} seconds")
        v1_apps = self.apps_v1_api
        ready_services = set()
        start_time = time.time()
        services = set(self.experiment.critical_services)
        namespace = self.experiment.namespace

        while len(ready_services) < len(services) and time.time() - start_time < timeout:
            for service in services.difference(ready_services):
                # Check StatefulSet status
                try:
                    statefulset_status = v1_apps.read_namespaced_stateful_set_status(service, namespace)
                    if statefulset_status.status.ready_replicas and statefulset_status.status.ready_replicas > 0:
                        ready_services.add(service)
                        continue
                except ApiException as e:
                    # Ignore not found errors
                    if e.status != 404:  
                        logger.error(f"Error checking status for service '{service}': {e}")
                # Check Deployment status
                try:
                    deployment_status = v1_apps.read_namespaced_deployment_status(service, namespace)
                    if deployment_status.status.ready_replicas and deployment_status.status.ready_replicas > 0:
                        ready_services.add(service)
                        continue
                except ApiException as e:
                    # Ignore not found errors
                    if e.status != 404:  
                        logger.error(f"Error checking status for service '{service}': {e}")
            if services == ready_services:
                logger.info("All services are up!")
                return True
            time.sleep(1)
        logger.error("Timeout reached. The following services are not ready: " + str(list(services - ready_services)))
        raise RuntimeError("Timeout reached. The following services are not ready: " + str(list(services - ready_services)))


    def clone_sut(self):
        """
        Clones the SUT repository if it doesn't exist.
        """
        if self.config.sut_config.helm_chart_repo:
            # If a helm chart repo is provided, clone it
            if self.sut_path.exists():
                logger.warning(f"SUT path {self.sut_path} already exists. It will not clone the repository again.")
            else: 
                logger.info(f"Cloning Helm chart repository from {self.config.sut_config.helm_chart_repo} to {self.sut_path}")
                subprocess.check_call(["git", "clone", self.config.sut_config.helm_chart_repo, str(self.sut_path)])
        elif not self.sut_path.exists():
            if not self.config.sut_config.sut_git_repo:
                raise ValueError("SUT Git repository URL is not provided in the configuration")
            logger.info(f"Cloning SUT from {self.config.sut_config.sut_git_repo} to {self.sut_path}")
            subprocess.check_call(["git", "clone", self.config.sut_config.sut_git_repo, str(self.sut_path)])
        else:
            logger.info(f"SUT already exists at {self.sut_path}. Skipping cloning.")


    def deploy_SUT(self):
        """
        Orchestrates the full deployment process for the experiment.
        """
        StatusManager.set(StatusPhase.DEPLOYING_SUT, "Deploying SUT...")
        # Check for namespace
        logger.info(f"Checking if namespace '{self.experiment.namespace}' exists")
        self._create_namespace_if_not_exists()
        # Check for nodes labels
        logger.info(f"Checking for nodes with label scaphandre=true")
        self._check_labeled_node_available()
        # Installs Prometheus, Kepler
        logger.info("Ensuring cluster observability requirements")
        self._ensure_helm_requirements() 
        # Clones the SUT repository
        self.clone_sut() 
        # Prepare the Helm wrapper as a context manager
        with self.helm_wrapper as wrapper:
            logger.info("Patching the helm chart")
            values = wrapper.update_helm_chart()
            # Create results folder
            logger.info("Creating results directory")
            self._creates_results_directory(values)
            # Deploy the SUT
            logger.info(f"Deploying the SUT: {ENV_CONFIG.SUT}")
            wrapper.deploy_sut()
        # Set the status
        StatusManager.set(StatusPhase.WAITING, "Waiting for system to stabilize...")
        # Wait for all critical services
        logger.info(f"Waiting for all critical services: [{set(self.experiment.critical_services)}]")
        self._wait_until_services_ready()
        if self.experiment.autoscaling:
            logger.info("Autoscaling is enabled. Deploying autoscaling...")
            AutoscalingDeployer(self.experiment).setup_autoscaling()
        else:
            logger.info("Autoscaling disabled. Skipping its deployment.")
        StatusManager.set(StatusPhase.WAITING, "Waiting for load generator...")
        logger.info("SUT deployment successful.")