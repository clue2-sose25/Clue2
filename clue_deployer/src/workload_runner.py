import base64
import os
import platform
import signal
import subprocess
import tarfile
from os import path
from tempfile import TemporaryFile
import docker
import logging
from kubernetes import client, watch, stream
from kubernetes.client.rest import ApiException
from clue_deployer.src.configs.configs import CLUE_CONFIG, SUT_CONFIG
from clue_deployer.src.models.variant import Variant
from clue_deployer.src.models.result_files import ResultFiles
from clue_deployer.src.models.workload import Workload
from clue_deployer.src.models.workload_cancelled_exception import WorkloadCancelled
from clue_deployer.src.logger import process_logger as logger


class WorkloadRunner:

    def __init__(self, variant: Variant, workload: Workload):
        self.variant = variant
        self.workload = workload
        self.result_filenames = ResultFiles(sut=SUT_CONFIG.sut)
        self._core_api = None
        self._observations_path = None
        self._port_forward_process = None
        self._docker_client = None
    
    def run_workload(self, outpath):
        if self.variant.colocated_workload:
            self._run_remote_workload(outpath)
        else:
            self._run_local_workload(outpath)

    def _cancel_remote_workload(self, sig=None, frame=None):
        """Cancel remote workload running in Kubernetes"""
        logger.info("Workload cancelled, stopping remote workload and deleting pod")
        # attempt to download results before deleting the pod
        self._download_results("loadgenerator", self._observations_path)
        
        # (force) delete the running pod to stop the workload
        if self._core_api:
            logger.info("Deleting loadgenerator pod in namespace %s", SUT_CONFIG.namespace)
            self._core_api.delete_collection_namespaced_pod(
                namespace=SUT_CONFIG.namespace,
                label_selector="app=loadgenerator",
                timeout_seconds=0,
                grace_period_seconds=0,
            )
        
        if platform.system() == "Windows":
            raise WorkloadCancelled("Workload cancelled")  # Raise exception on Windows

    def _cancel_local_workload(self, sig, frame):
        """Cancel local workload running in Docker"""
        logger.info("Workload cancelled, stopping port forward and loadgenerator container")
        
        if self._port_forward_process:
            self._port_forward_process.kill()
        
        if self._docker_client:
            try:
                self._docker_client.containers.get("loadgenerator").kill()
            except:
                pass

    def _run_remote_workload(self, outpath):
        logger.info("Deploying workload remotely in Kubernetes cluster")
        self._observations_path = os.path.join(outpath, "")  # ensure trailing slash for later path building
        self._core_api = client.CoreV1Api()

        # Set up SIGUSR1 handler only on Unix-like systems
        if platform.system() != "Windows":
            signal.signal(signal.SIGUSR1, self._cancel_remote_workload)

        config_map_names = []
        try:
            config_map_names = self._deploy_remote_workload(self._core_api)
            self._wait_for_workload(self._core_api, self._observations_path)
        except WorkloadCancelled:
            logging.info("Remote workload stopped due to cancellation")
        finally:
            logger.info("Deleting loadgenerator pod in namespace %s", SUT_CONFIG.namespace)
            self._core_api.delete_namespaced_pod(name="loadgenerator", namespace=SUT_CONFIG.namespace)
            for config_map_name in config_map_names:
                try:
                    self._core_api.delete_namespaced_config_map(name=config_map_name, namespace=SUT_CONFIG.namespace)
                    logger.info(f"Deleted ConfigMap {config_map_name}")
                except ApiException as e:
                    if e.status != 404:
                        logger.error(f"Failed to delete ConfigMap {config_map_name}: {e}")

    def _wait_for_workload(self, core: client.CoreV1Api, observations: str):
        """
            This watches the pod events until it is finished.
        """
        logger.info("The experiment is running now. Waiting for it to finish which will take approximately %d seconds", self.workload.workload_runtime)
        w = watch.Watch()
        
        for event in w.stream(
                core.list_namespaced_pod,
                SUT_CONFIG.namespace,
                label_selector="app=loadgenerator",
                timeout_seconds=self.workload.timeout_duration,
            ):
            pod = event["object"]
            if pod.status.container_statuses and pod.status.container_statuses[0].state.terminated:
                logger.info("Loadgenerator container terminated!")
                try:
                    self._download_results("loadgenerator", observations)
                finally:
                    w.stop()
                    return
            elif pod.status.phase == "Failed":
                logger.error(f"loadgenerator pod failed! {pod}")
                try:
                    logger.info(f"Attempting to download results from failed pod, just in case")
                    self._download_results("loadgenerator", observations)
                finally:
                    w.stop()
                    return

        # workload did not finish during the defined timeout
        logger.error("Workload pod did not finish within the timeout period, can not download results")

    def _deploy_remote_workload(self, core: client.CoreV1Api):
        def k8s_env_pair(k, v):
            return client.V1EnvVar(
                name=k,
                value=str(v)
            )

        container_env = [k8s_env_pair(k, v) for k, v in self.workload.workload_settings.items() if k != "LOCUST_RUN_TIME"]
        
        # Ensure that the host reflects the colocated case
        container_env.append(
            client.V1EnvVar(
                name="LOCUST_HOST",
                value= SUT_CONFIG.target_host
            )
        )
        
        # Ensure that the SUT name is set in the environment
        container_env.append(
            client.V1EnvVar(
                name="SUT_NAME",
                value= SUT_CONFIG.sut
            )
        )

        locust_volumes = []
        locust_volume_mounts = []
        locust_file_paths_in_container = []
        config_map_names = []

        # Create a ConfigMap for each locust file and its corresponding volume mount
        for idx, file_path_relative in enumerate(self.workload.locust_files):
            full_locust_file_path_in_deployer = os.path.join("/app", file_path_relative)
            
            # Read the content of the locust file
            with open(full_locust_file_path_in_deployer, 'r') as f:
                locust_file_content = f.read()

            # Create a unique name for the ConfigMap
            config_map_name = f"locustfile-{self.workload.name}-{idx}"
            config_map_names.append(config_map_name)
            
            # Get the original filename
            original_filename = os.path.basename(file_path_relative)

            # Create the ConfigMap containing the locust file
            config_map_body = client.V1ConfigMap(
                api_version="v1",
                kind="ConfigMap",
                metadata=client.V1ObjectMeta(name=config_map_name, namespace=SUT_CONFIG.namespace),
                data={original_filename: locust_file_content} # Use original filename as key
            )
            core.create_namespaced_config_map(namespace=SUT_CONFIG.namespace, body=config_map_body)
            logger.info(f"Created ConfigMap {config_map_name} for {original_filename}")

            # Define the mount path inside the loadgenerator container
            mount_path_in_container = f"/app/locustfiles/{original_filename}"
            locust_file_paths_in_container.append(mount_path_in_container)

            # Add volume for the ConfigMap
            locust_volumes.append(
                client.V1Volume(
                    name=f"locustfile-volume-{idx}",
                    config_map=client.V1ConfigMapVolumeSource(name=config_map_name)
                )
            )

            # Add volume mount for the ConfigMap
            locust_volume_mounts.append(
                client.V1VolumeMount(
                    name=f"locustfile-volume-{idx}",
                    mount_path=mount_path_in_container,
                    sub_path=original_filename # Locustfile is saved with its original name in the config map
                )
            )
        
        # Pass locust files location to container via LOCUST_FILE environment variable
        container_env.append(
            client.V1EnvVar(
                name="LOCUST_RUN_TIME",
                value=f"{self.workload.workload_runtime}s"
            )
        )
        container_env.append(
            client.V1EnvVar(
                name="LOCUST_FILE",
                value=",".join(locust_file_paths_in_container)
            )
        )

        logger.debug("Using the workload container env: %s", container_env)

        # Make sure that the loadgenerator runs on a seperate node
        affinity = client.V1Affinity(
                        node_affinity=client.V1NodeAffinity(
                            required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
                                node_selector_terms=[
                                    client.V1NodeSelectorTerm(
                                        match_expressions=[
                                            client.V1NodeSelectorRequirement(
                                                key="scaphandre", operator="DoesNotExist"
                                            )
                                        ]
                                    )
                                ]
                            )
                        ),
                    ) 

        core.create_namespaced_pod(
            namespace=SUT_CONFIG.namespace,
            body=client.V1Pod(
                metadata=client.V1ObjectMeta(
                    name="loadgenerator",
                    namespace=SUT_CONFIG.namespace,
                    labels={"app": "loadgenerator"},
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="loadgenerator",
                            image=f"{CLUE_CONFIG.docker_registry_address}/clue-loadgenerator:latest",
                            env=container_env,
                            command=["/bin/bash", "-c", "./entrypoint.sh"],
                            working_dir="/app",
                            volume_mounts=locust_volume_mounts,
                        )
                    ],
                    volumes=locust_volumes,
                    # Run this on a different node
                    affinity=affinity,
                    restart_policy="Never",
                ),
            ),
        )
        logger.info("Deployed loadgenerator to cluster!")
        return config_map_names

    def _download_results(self, pod_name: str, results_path: str):
        """
        Downloads the results from the pods
        """
        try:
            core = client.CoreV1Api()
            resp = core.read_namespaced_pod_log(name=pod_name, namespace=SUT_CONFIG.namespace)
            log_contents = resp
            if not log_contents or len(log_contents) == 0:
                logger.error(f"{pod_name} in namespace {SUT_CONFIG.namespace} has no logs, workload failed?")
                return 
            
            with TemporaryFile() as tar_buffer:
                tar_buffer.write(base64.b64decode(log_contents))
                tar_buffer.seek(0)

                with tarfile.open(
                        fileobj=tar_buffer,
                        mode="r:gz",
                ) as tar:
                    tar.extractall(path=results_path)
            logger.info(f"Succesfully downloaded results from pod {pod_name} in namespace {SUT_CONFIG.namespace} to {results_path}!")
        except ApiException as e:
            logger.error(f"failed to get log from pod {pod_name} in namespace {SUT_CONFIG.namespace}: %s", e)
        except tarfile.TarError as e:
            logger.error(f"failed to extract log from TAR", e, log_contents)
        except Exception as e:
            logger.error("failed to extraxt log",e,log_contents)
            

    def _run_local_workload(self, outpath):
        logger.info("Deploying workload locally in docker container on host machine")
        observations = outpath
        self._docker_client = docker.from_env()

        # Port forward the sut service on the local machine
        self._port_forward_process = subprocess.Popen(
            [
                "kubectl",
                "-n",
                SUT_CONFIG.namespace,
                "port-forward",
                "--address",
                "0.0.0.0",
                f"services/{SUT_CONFIG.target_service_name}",
                f"{CLUE_CONFIG.local_port}:80",
            ],
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Create locust stats paths for mounting them into the container
        mounts = {
            path.abspath(path.join(observations, "locust_stats.csv")): {
                "bind": f"/loadgenerator/{self.result_filenames.stats_csv}",
                "mode": "rw",
            },
            path.abspath(path.join(observations, "locust_failures.csv")): {
                "bind": f"/loadgenerator/{self.result_filenames.failures_csv}",
                "mode": "rw",
            },
            path.abspath(path.join(observations, "locust_stats_history.csv")): {
                "bind": f"/loadgenerator/{self.result_filenames.stats_history_csv}",
                "mode": "rw",
            },
            path.abspath(path.join(observations, "locust_report.html")): {
                "bind": f"/loadgenerator/{self.result_filenames.report}",
                "mode": "rw",
            },
        }

        locust_file_paths_in_container = []
        for idx, file_path_relative in enumerate(self.workload.locust_files):
            # Construct the full path to the locust file inside the deployer container
            full_locust_file_path_in_deployer = os.path.join("/app", file_path_relative)
            
            # Define the mount path inside the loadgenerator container
            original_filename = os.path.basename(file_path_relative)
            mount_path_in_container = f"/app/locustfiles/{original_filename}"
            locust_file_paths_in_container.append(mount_path_in_container)

            mounts[os.path.abspath(full_locust_file_path_in_deployer)] = { # Use full_locust_file_path_in_deployer as key
                "bind": mount_path_in_container,
                "mode": "ro",
            }

        # create files for the mounts if they do not exist
        for f in mounts.keys():
            if not os.path.isfile(f):
                with open(f, "w") as f:
                    pass

        # Set up signal handler for local workload cancellation
        signal.signal(signal.SIGUSR1, self._cancel_local_workload)

        try:
            print("Running the workload generator")
            workload = self._docker_client.containers.run(
                image=f"{CLUE_CONFIG.docker_registry_address}/loadgenerator:latest",
                auto_remove=True,
                environment={
                    **{k: v for k, v in self.workload.workload_settings.items() if k != "LOCUST_RUN_TIME"},
                    "LOCUST_RUN_TIME": f"{self.workload.workload_runtime}s",
                    "LOCUST_FILE": ",".join(locust_file_paths_in_container),
                    "LOCUST_HOST": SUT_CONFIG.target_host,
                    "SUT_NAME": SUT_CONFIG.sut
                },
                stdout=True,
                stderr=True,
                volumes=mounts,
                name="loadgenerator",
            )
            with open(path.join(observations, "docker.log"), "w") as f:
                f.write(workload)
        except Exception as e:
            logger.error("failed to run workload in docker container", e)
        
        if self._port_forward_process:
            self._port_forward_process.kill()