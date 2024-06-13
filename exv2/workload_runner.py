import base64
import os
import signal
import subprocess
import tarfile
from os import path
from tempfile import TemporaryFile

import docker
from kubernetes import client, watch
from kubernetes.client.rest import ApiException

from experiment import Experiment


class WorkloadRunner:

    def __init__(self, experiment: Experiment):
        self.exp = experiment
        wls = self.exp.env.workload_settings

        self.workload_env = {
                                "LOADGENERATOR_MAX_DAILY_USERS": wls["LOADGENERATOR_MAX_DAILY_USERS"],
                                # The maximum daily users.
                                "LOADGENERATOR_STAGE_DURATION": wls["LOADGENERATOR_STAGE_DURATION"],
                                # The duration of a stage in seconds.
                                "LOADGENERATOR_USE_CURRENTTIME": "n",
                                # using current time to drive worload (e.g. day/night cycle)
                                "LOADGENERATOR_ENDPOINT_NAME": "Vanilla",  # the workload profile
                                "LOCUST_HOST": f"http://{self.exp.env.local_public_ip}:{self.exp.env.local_port}/tools.descartes.teastore.webui",
                                # endpoint of the deployed service,
                                # "LOCUST_LOCUSTFILE": wls["LOCUSTFILE"],
                            } | self.exp.env.workload_settings
        

    def build_workload(
            self, workload_branch: str = "priv/lierseleow/loadgenerator"
    ):
        """
        build the workload image as a docker image, either to be deployed locally or colocated with the service
        """

        docker_client = docker.from_env()

        exp = self.exp

        platform = (
            exp.env.local_platform_arch
            if exp.colocated_workload
            else exp.env.remote_platform_arch
        )

        build = subprocess.check_call(
            [
                "docker",
                "buildx",
                "build",
                "--platform",
                platform,
                "-t",
                f"{exp.env.docker_user}/loadgenerator",
                ".",
            ],
            cwd=path.join("loadgenerator"),
        )
        if build != 0:
            raise RuntimeError(f"failed to build {workload_branch}")

        docker_client.images.push(f"{exp.env.docker_user}/loadgenerator")

    def run_workload(self):
        if self.exp.colocated_workload:
            self._run_remote_workload()
        else:
            self._run_local_workload()

    def _run_remote_workload(self, observations: str = "data"):
        core = client.CoreV1Api()
        exp = self.exp

        def cancel(sig, frame):
            core.delete_collection_namespaced_pod(
                namespace=exp.namespace,
                label_selector="app=loadgenerator",
                timeout_seconds=0,
                grace_period_seconds=0,
            )

        signal.signal(signal.SIGUSR1, cancel)

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
                value=f"http://teastore-webui/tools.descartes.teastore.webui")
        )
        # container_env = [
        #     client.V1EnvVar(
        #         name="LOADGENERATOR_MAX_DAILY_USERS",
        #         value=str(exp.env.workload_settings["LOADGENERATOR_MAX_DAILY_USERS"]),
        #     ),
        #     client.V1EnvVar(
        #         name="LOADGENERATOR_STAGE_DURATION",
        #         value=str(exp.env.workload_settings["LOADGENERATOR_STAGE_DURATION"]),
        #     ),
        #     client.V1EnvVar(name="LOADGENERATOR_USE_CURRENTTIME", value="n"),
        #     client.V1EnvVar(name="LOADGENERATOR_ENDPOINT_NAME", value="Vanilla"),
        #     client.V1EnvVar(
        #         name="LOCUST_HOST",
        #         value=f"http://teastore-webui/tools.descartes.teastore.webui"
        #     ),
        #     client.V1EnvVar(name="LOCUST_LOCUSTFILE", value=env["workload"]["LOCUSTFILE"]),
        # ]

        # again, new patching scheme: we'll just apply the entire (already patched) workload
        # settings from the experiment here
        # 
        # old:
        # this may overwrite the env vars above, be careful
        # if "workload" in exp.env_patches:
        #     for k, v in exp.env_patches["workload"].items():
        #         container_env.append(client.V1EnvVar(name=f"LOCUST_{k}", value=str(v)))

        # print("DEBUG: env for new namespaced pod:")
        # print(container_env)

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
                            image=f"{exp.env.docker_user}/loadgenerator",
                            env=container_env,
                            command=[
                                "sh",
                                "-c",
                                "locust --csv teastore --csv-full-history --headless --only-summary 1>/dev/null 2>erros.log || tar zcf - teastore_stats.csv teastore_failures.csv teastore_stats_history.csv erros.log | base64 -w 0",
                            ],
                            working_dir="/loadgenerator",
                        )
                    ],
                    # run this on a differnt node
                    affinity=client.V1Affinity(
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
                    ),
                    restart_policy="Never",
                ),
            ),
        )

        w = watch.Watch()
        for event in w.stream(
                core.list_namespaced_pod,
                exp.namespace,
                label_selector="app=loadgenerator",
                timeout_seconds=self.workload_env["LOADGENERATOR_STAGE_DURATION"] * 8 + 60,
        ):
            pod = event["object"]
            if pod.status.phase == "Succeeded" or pod.status.phase == "Completed":
                self._download_results("loadgenerator", observations)
                print("container finished, downloading results")
                w.stop()
            elif pod.status.phase == "Failed":
                print("workload could not be started...", pod)
                self._download_results("loadgenerator", observations)
                w.stop()
        # TODO: deal with still running workloads

        core.delete_namespaced_pod(name="loadgenerator", namespace=exp.namespace)

    # noinspection PyUnboundLocalVariable
    def _download_results(self, pod_name: str, destination_path: str):

        namespace = self.exp.namespace

        try:
            core = client.CoreV1Api()
            resp = core.read_namespaced_pod_log(name=pod_name, namespace=namespace)
            log_contents = resp
            if not log_contents or len(log_contents) == 0:
                print(f"{pod_name} in namespace {namespace} has no logs, workload failed?")
            with TemporaryFile() as tar_buffer:
                tar_buffer.write(base64.b64decode(log_contents))
                tar_buffer.seek(0)

                with tarfile.open(
                        fileobj=tar_buffer,
                        mode="r:gz",
                ) as tar:
                    tar.extractall(path=destination_path)
        except ApiException as e:
            print(f"failed to get log from pod {pod_name} in namespace {namespace}", e)
        except tarfile.TarError as e:
            print(f"failed to extract log", e, log_contents)

    def _run_local_workload(self, observations: str = "data"):

        docker_client = docker.from_env()

        forward = subprocess.Popen(
            [
                "kubectl",
                "-n",
                self.exp.namespace,
                "port-forward",
                "--address",
                "0.0.0.0",
                "services/teastore-webui",
                f"{self.exp.env.local_port}:80",
            ],
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # create locust stats files
        mounts = {
            path.abspath(path.join(observations, "locust_stats.csv")): {
                "bind": "/loadgenerator/teastore_stats.csv",
                "mode": "rw",
            },
            path.abspath(path.join(observations, "locust_failures.csv")): {
                "bind": "/loadgenerator/teastore_failures.csv",
                "mode": "rw",
            },
            path.abspath(path.join(observations, "locust_stats_history.csv")): {
                "bind": "/loadgenerator/teastore_stats_history.csv",
                "mode": "rw",
            },
            path.abspath(path.join(observations, "locust_report.html")): {
                "bind": "/loadgenerator/teastore_report.html",
                "mode": "rw",
            },
        }

        # todo: what does this do
        for f in mounts.keys():
            if not os.path.isfile(f):
                with open(f, "w") as f:
                    pass

        # TODO: XXX get local ip to use for locust host
        def cancel(sig, frame):
            forward.kill()
            try:
                docker_client.containers.get("loadgenerator").kill()
            except:
                pass
            print("local workload timeout reached.")

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
                image=f"{self.exp.env.docker_user}/loadgenerator",
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
            print("failed to run workload properly", e)
        forward.kill()
