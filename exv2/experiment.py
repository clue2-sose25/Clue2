from typing import List
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
            max_autoscale: int = 3,
            critical_services:List[str]=["teastore-auth", "teastore-registry", "teastore-webui"],
            target_host:str="http://teastore-webui/tools.descartes.teastore.webui",
            infrastrcutre_namespaces:List[str] = [],

            # env = ExperimentEnvironment
    ):

        # metadata
        self.name = name
        self.target_branch = target_branch
        self.namespace = namespace
        self.infrastrcutre_namespaces = infrastrcutre_namespaces
        self.critical_services=critical_services
        # self.patches = patches
        self.target_host = target_host

        # observability data
        self.prometheus = prometheus_url
        self.colocated_workload = colocated_workload

        self.env = ExperimentEnvironment.from_config()
        self.autoscaling = autoscaling
        if autoscaling is not None:
            self.env.tags.append("scale")

        self.max_autoscale = max_autoscale

    def __str__(self) -> str:
        if self.autoscaling:
            return f"{self.name}_{self.target_branch}_{self.autoscaling}".replace(
                "/", "_"
            )
        else:
            return f"{self.name}_{self.target_branch}".replace("/", "_")

    def to_row(self):
        return [self.name, self.target_branch, self.namespace, self.autoscaling, self.env.tags]

    @staticmethod
    def headers():
        return ["Name", "Branch", "Namespace", "Autoscaling", "Env Tags"]

    def create_json(self, env: dict = {}):

        env = ExperimentEnvironment().from_config().__dict__

        description = {
            "name": self.name,
            "target_branch": self.target_branch,
            "namespace": self.namespace,
            # "patches": self.patches,
            "executor": "colocated" if self.colocated_workload else "local",
            "scaling": str(self.autoscaling),
            # "env_patches": self.env_patches,
        }
        description = description | env
        return json.dumps(description)
