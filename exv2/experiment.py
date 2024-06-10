from os import path
import signal
import json
import subprocess
import kubernetes


from psc import ResourceTracker, NodeUsage
from datetime import datetime



from flushing_queue import FlushingQueue
from scaling_experiment_setting import ScalingExperimentSetting
from experiment_environment import ExperimentEnvironment



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
        
    def to_row(self): return [self.name, self.target_branch, self.namespace, self.patches]
    def headers(): return ["Name", "Branch", "Namespace", "Patches"]

    def create_json(self, env: dict = {}):


        env = ExperimentEnvironment().__dict__()

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
 
  

            
