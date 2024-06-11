from os import path
import json

from scaling_experiment_setting import ScalingExperimentSetting
from experiment_environment import ExperimentEnvironment


class Experiment:


    def __init__(
        
        self,
        name: str,
        target_branch: str,
        namespace: str,
        colocated_workload: bool = False,
        prometheus_url: str = "http://localhost:9090",
        autoscaling: ScalingExperimentSetting = None,
        # env = ExperimentEnvironment
    ):


        # metadata
        self.name = name
        self.target_branch = target_branch
        self.namespace = namespace
        # self.patches = patches

        # observability data
        self.prometheus = prometheus_url
        self.colocated_workload = colocated_workload
        self.autoscaling = autoscaling
        self.env = ExperimentEnvironment()

    def __str__(self) -> str:
        if self.autoscaling:
            return f"{self.name}_{self.target_branch}_{self.autoscaling}".replace(
                "/", "_"
            )
        else:
            return f"{self.name}_{self.target_branch}".replace("/", "_")
        
    def to_row(self): return [self.name, self.target_branch, self.namespace, self.autoscaling, self.env.tags]
    def headers(): return ["Name", "Branch", "Namespace", "Autoscaling", "Env Tags"]

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
 
  

            
