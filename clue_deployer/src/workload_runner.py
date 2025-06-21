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
from clue_deployer.src.experiment import Experiment
from clue_deployer.src.result_files import ResultFiles
from clue_deployer.src.workload_cancelled_exception import WorkloadCancelled
from clue_deployer.src.logger import logger


class WorkloadRunner:

    def __init__(self, experiment: Experiment):
        self.exp = experiment
        wls = self.exp.env.workload_settings
        self.config = experiment.config

        self.workload_env = {
                                # The duration of a stage in seconds.
                                "LOADGENERATOR_USE_CURRENTTIME": "n",
                                # using current time to drive worload (e.g. day/night cycle)
                                "LOADGENERATOR_ENDPOINT_NAME": "Vanilla",  # the workload profile
                                "LOCUST_HOST": f"http://{self.exp.env.local_public_ip}:{self.exp.env.local_port}{self.config.sut_config.application_endpoint_path}",
                                # endpoint of the deployed service,
                                # "LOCUST_LOCUSTFILE": wls["LOCUSTFILE"],
                            } | self.exp.env.workload_settings
        
        self.sut_name = self.exp.config.sut_config.sut_name
        self.result_filenames = ResultFiles(sut_name=self.sut_name)
    
    def run_workload(self, outpath):
        if self.exp.colocated_workload:
            self._run_remote_workload(outpath)
        else:
            self._run_local_workload(outpath)

    def _run_remote_workload(self, outpath):
        logger.info("Deploying workload remotely in Kubernetes cluster")
        observations = os.path.join(outpath, "")  # ensure trailing slash for later path building
        core = client.CoreV1Api()
        exp = self.exp

        def cancel(sig=None, frame=None):
            logger.info("Workload cancelled, stopping remote workload and deleting pod")
            # attempt to download results before deleting the pod
            self._download_results("loadgenerator", observations)
            # (force) delete the running pod to stop the workload
            logger.info("Deleting loadgenerator pod in namespace %s", exp.namespace)
            core.delete_collection_namespaced_pod(
                namespace=exp.namespace,
                label_selector="app=loadgenerator",
                timeout_seconds=0,
                grace_period_seconds=0,
            )
            if platform.system() == "Windows":
                raise WorkloadCancelled("Workload cancelled")  # Raise exception on Windows

        # Set up SIGUSR1 handler only on Unix-like systems
        if platform.system() != "Windows":
            signal.signal(signal.SIGUSR1, cancel)

        try:
            self._deploy_remote_workload(exp, core)

            self._wait_for_workload(core, exp, observations)

            logger.info("Deleting loadgenerator pod in namespace %s", exp.namespace)
            core.delete_namespaced_pod(name="loadgenerator", namespace=exp.namespace)
        except WorkloadCancelled:
            logging.info("Remote workload stopped due to cancellation")

    def _wait_for_workload(self, core: client.CoreV1Api, exp: Experiment, observations: str):
        """
            this continuesly watches the pod until it is finished in 60s intervals
            should the pod disappear before it finishes, we stop waiting.
        """
        finished = False
        logger.info("The experiment is running now. Waiting until the loadgenerator is finished...")
        while not finished:
            w = watch.Watch()
            for event in w.stream(
                    core.list_namespaced_pod,
                    exp.namespace,
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
                pod_list = core.list_namespaced_pod(exp.namespace, label_selector="app=loadgenerator")
                if len(pod_list.items) == 0:
                    logger.error("workload pod was not found, did it fail to start?, can't download results")
                    finished = True


    def _deploy_remote_workload(self, exp: Experiment, core: client.CoreV1Api):
        def k8s_env_pair(k, v):
            return client.V1EnvVar(
                name=k,
                value=str(v)
            )

        container_env = [k8s_env_pair(k, v) for k, v in exp.env.workload_settings.items()]
        #ensure that the host reflects the colocated case
        container_env.append(
            client.V1EnvVar(
                name="LOCUST_HOST",
                value=exp.target_host
            )
        )

        logger.debug("using workload container env: %s", container_env)


        # make sure that the loadgenerator runs on a seperate node, unless we're using e.g. minikube
        if 'dirty' not in exp.env.tags:
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
        else:
            affinity=None


        core.create_namespaced_pod(
            namespace=exp.namespace,
            body=client.V1Pod(
                metadata=client.V1ObjectMeta(
                    name="loadgenerator",
                    namespace=exp.namespace,
                    labels={"app": "loadgenerator"},
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="loadgenerator",
                            image=f"{exp.env.docker_registry_address}/loadgenerator:vanilla",
                            env=container_env,
                            command=[
                                "sh",
                                "-c",
                                f"locust --csv {self.sut_name} --csv-full-history --headless --only-summary 1>/dev/null 2>errors.log; tar zcf - {self.result_filenames.stats_csv} {self.result_filenames.failures_csv} {self.result_filenames.stats_history_csv} errors.log | base64 -w 0",
                            ],
                            working_dir="/loadgenerator",
                        )
                    ],
                    # run this on a differnt node
                    affinity=affinity,
                    restart_policy="Never",
                ),
            ),
        )
        logger.info("Deployed loadgenerator to cluster!")

    # noinspection PyUnboundLocalVariable
    def _download_results(self, pod_name: str, destination_path: str):

        namespace = self.exp.namespace

        try:
            core = client.CoreV1Api()
            resp = core.read_namespaced_pod_log(name=pod_name, namespace=namespace)
            log_contents = resp
            if not log_contents or len(log_contents) == 0:
                logger.error(f"{pod_name} in namespace {namespace} has no logs, workload failed?")
                return 
            
            with TemporaryFile() as tar_buffer:
                tar_buffer.write(base64.b64decode(log_contents))
                tar_buffer.seek(0)

                with tarfile.open(
                        fileobj=tar_buffer,
                        mode="r:gz",
                ) as tar:
                    tar.extractall(path=destination_path)
            logger.info(f"Succesfully downloaded results from pod {pod_name} in namespace {namespace} to {destination_path}!")
        except ApiException as e:
            logger.error(f"failed to get log from pod {pod_name} in namespace {namespace}: %s", e)
        except tarfile.TarError as e:
            logger.error(f"failed to extract log from TAR", e, log_contents)
        except Exception as e:
            logger.error("failed to extraxt log",e,log_contents)
            

    def _run_local_workload(self, outpath):
        logger.info("Deploying workload locally in docker container on host machine")
        observations = outpath
        docker_client = docker.from_env()

        # port forward the sut service on the local machine
        forward = subprocess.Popen(
            [
                "kubectl",
                "-n",
                self.exp.namespace,
                "port-forward",
                "--address",
                "0.0.0.0",
                f"services/{self.config.sut_config.target_service_name}",
                f"{self.exp.env.local_port}:80",
            ],
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # create locust stats paths for mounting them into the container
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

        # TODO: XXX get local ip to use for locust host
        def cancel(sig, frame):
            logger.info("Workload cancelled, stopping port forward and loadgenerator container")
            forward.kill()
            try:
                docker_client.containers.get("loadgenerator").kill()
            except:
                pass

        signal.signal(signal.SIGUSR1, cancel)

        # todo: this could probably be all moved into experiment env?
        # or even a new workload env?

        # new patching strategy!
        # patches are directly applied into the experiments env and signified by exp.tags now
        # 
        # if "workload" in exp.env_patches:
        #     for k, v in exp.env_patches["workload"].items():
        #         workload_env[f"LOCUST_{k}"] = v

        try:
            print("🏋️‍♀️ running loadgenerator")
            workload = docker_client.containers.run(
                image=f"{self.exp.env.docker_registry_address}/loadgenerator",
                auto_remove=True,
                environment=self.workload_env,
                stdout=True,
                stderr=True,
                volumes=mounts,
                name="loadgenerator",
            )
            with open(path.join(observations, "docker.log"), "w") as f:
                f.write(workload)
        except Exception as e:
            logger.error("failed to run workload in docker container", e)
        forward.kill()
