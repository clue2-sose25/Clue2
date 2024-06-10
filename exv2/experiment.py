from os import path
import signal
import subprocess

from psc import ResourceTracker, NodeUsage
from datetime import datetime

from flushing_queue import FlushingQueue
from scaling_experiment_setting import ScalingExperimentSetting
from workload_runner import WorkloadRunner

class Experiment:

    def __init__(
        self,
        name: str,
        target_branch: str,
        namespace: str,
        colocated_workload: bool = False,
        patches: list = [],
        prometheus_url: str = "http://localhost:9090",
        autoscaling: ScalingExperimentSetting = None,
        env_patches: dict = {},
    ):
        # metadata
        self.name = name
        self.target_branch = target_branch
        self.namespace = namespace
        self.patches = patches

        # observability data
        self.prometheus = prometheus_url
        self.colocated_workload = colocated_workload
        self.autoscaling = autoscaling
        self.env_patches = env_patches

    def __str__(self) -> str:
        if self.autoscaling:
            return f"{self.name}_{self.target_branch}_{self.autoscaling}".replace(
                "/", "_"
            )
        else:
            return f"{self.name}_{self.target_branch}".replace("/", "_")

    def create_json(self, env: dict = {}):
        import json

        description = {
            "name": self.name,
            "target_branch": self.target_branch,
            "namespace": self.namespace,
            "patches": self.patches,
            "executor": "colocated" if self.colocated_workload else "local",
            "scaling": str(self.autoscaling),
            "env_patches": self.env_patches,
        }
        description = description | env
        return json.dumps(description)
 
    def run(self, observations_out_path: str = "data/default"):


        datafile = path.join(
            observations_out_path, f"measurements_{datetime.now().strftime('%d_%m_%Y_%H_%M')}.csv"
        )
        observations_out_path_channel = FlushingQeueu(
            datafile, buffer_size=32, fields=NodeUsage._fields
        )
        tracker = ResourceTracker(self.prometheus, observations_out_path_channel, self.namespace, 10)

        with open(path.join(observations_out_path, "experiment.json"), "w") as f:
            f.write(self.createJson(env))

        # 5. start workload
        # start resouce tracker
        tracker.start()

        def cancel(sig, frame):
            tracker.stop()
            observations_channel.flush()
            signal.raise_signal(signal.SIGUSR1)  # raise signal to stop workload
            print("workload timeout reached.")

        signal.signal(signal.SIGALRM, cancel)

        # MAIN timeout to kill the experiment after 2 min after the workload should be compleated
        # 8 stages + 2 minutes to deploy and cleanup
        timeout = 8 * env["workload"]["LOADGENERATOR_STAGE_DURATION"] + 120
        print(f"starting workout with timeout {timeout}")
        signal.alarm(timeout)  

        # deploy workload on differnt node or localy and wait for workload to be compleated (or timeout)
        wlr = WorkloadRunner(experiment=self)
        # will run remotely or locally based on experiment
        wlr.run_workload()

        # stop resource tracker
        tracker.stop()
        observations_channel.flush()
        signal.alarm(0)  # cancel alarm