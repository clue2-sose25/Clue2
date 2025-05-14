from typing import List
import json
from pathlib import Path

from clue_deployer.scaling_experiment_setting import ScalingExperimentSetting
from clue_deployer.experiment_environment import ExperimentEnvironment


class Experiment:
    def __init__(
            self,
            name: str,
            target_branch: str,
            namespace: str,
            prometheus_url: str,
            critical_services: List[str],
            target_host: str,
            env: ExperimentEnvironment,
            colocated_workload: bool = False,
            autoscaling: ScalingExperimentSetting = None,
            max_autoscale: int = 3,
            infrastructure_namespaces: List[str] = [],
    ):
        # metadata
        self.name = name
        self.target_branch = target_branch
        self.namespace = namespace
        self.infrastructure_namespaces = infrastructure_namespaces
        self.critical_services = critical_services
        self.target_host = target_host

        # observability data
        self.prometheus = prometheus_url
        self.colocated_workload = colocated_workload

        self.env = env
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

    def create_json(self) -> str:
        description = {
            "name": self.name,
            "target_branch": self.target_branch,
            "namespace": self.namespace,
            "executor": "colocated" if self.colocated_workload else "local",
            "scaling": str(self.autoscaling),
        }

        # Convert Path objects in self.env.__dict__ to strings
        env_dict = {}
        for key, value in self.env.__dict__.items():
            if isinstance(value, Path):
                env_dict[key] = str(value)  # Convert Path to string
            else:
                env_dict[key] = value

        description = description | env_dict
        return json.dumps(description)