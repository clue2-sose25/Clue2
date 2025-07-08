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
from kubernetes import client, watch
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
        self.result_filenames = ResultFiles(sut=self.sut)
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
        if self._observations_path:
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

        try:
            self._deploy_remote_workload(self._core_api)
            self._wait_for_workload(self._core_api, self._observations_path)
            logger.info("Deleting loadgenerator pod in namespace %s", SUT_CONFIG.namespace)
            self._core_api.delete_namespaced_pod(name="loadgenerator", namespace=SUT_CONFIG.namespace)
        except WorkloadCancelled:
            logging.info("Remote workload stopped due to cancellation")

    def _wait_for_workload(self, core: client.CoreV1Api, observations: str):
        """
            This continuesly watches the pod until it is finished in 60s intervals.
            Should the pod disappear before it finishes, we stop waiting.
        """
        finished = False
        logger.info("The experiment is running now. Waiting until the loadgenerator is finished...")
        while not finished:
            w = watch.Watch()
            for event in w.stream(
                    core.list_namespaced_pod,
                    SUT_CONFIG.namespace,
                    label_selector="app=loadgenerator",
                    timeout_seconds=60,
            ):
                pod = event["object"]
                if pod.status.phase == "Succeeded" or pod.status.phase == "Completed":
                    logger.info("Loadgenerator container finished!")
                    try:
                        self._download_results("loadgenerator", observations)
                    finally:
                        w.stop()
                        finished = True
                elif pod.status.phase == "Failed":
                    logger.error(f"loadgenerator could not be started... {pod}")
                    try:
                        logger.info(f"Attempting to download results from failed pod, just in case")
                        self._download_results("loadgenerator", observations)
                    finally:
                        w.stop()
                        finished = True

            if not finished:
                # workload did not finish during the watch repeat
                pod_list = core.list_namespaced_pod(SUT_CONFIG.namespace, label_selector="app=loadgenerator")
                if len(pod_list.items) == 0:
                    logger.error("workload pod was not found, did it fail to start?, can't download results")
                    finished = True

    def _deploy_remote_workload(self, core: client.CoreV1Api):
        def k8s_env_pair(k, v):
            return client.V1EnvVar(
                name=k,
                value=str(v)
            )

        container_env = [k8s_env_pair(k, v) for k, v in self.workload.workload_settings.items()]
        # Ensure that the host reflects the colocated case
        container_env.append(
            client.V1EnvVar(
                name="LOCUST_HOST",
                value= SUT_CONFIG.target_host
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
                            image=f"{CLUE_CONFIG.docker_registry_address}/loadgenerator:{self.variant.target_branch}",
                            env=container_env,
                            command=[
                                "sh",
                                "-c",
                                f"locust --csv {SUT_CONFIG.sut} --csv-full-history --headless --only-summary 1>/dev/null 2>errors.log; tar zcf - {self.result_filenames.stats_csv} {self.result_filenames.failures_csv} {self.result_filenames.stats_history_csv} errors.log | base64 -w 0",
                            ],
                            working_dir="/loadgenerator",
                        )
                    ],
                    # Run this on a different node
                    affinity=affinity,
                    restart_policy="Never",
                ),
            ),
        )
        logger.info("Deployed loadgenerator to cluster!")

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
                image=f"{CLUE_CONFIG.docker_registry_address}/loadgenerator",
                auto_remove=True,
                environment=self.workload.workload_settings,
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