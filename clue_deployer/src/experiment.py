from typing import List
import json
from pathlib import Path

from config import Config
from clue_deployer.src.scaling_experiment_setting import ScalingExperimentSetting
from clue_deployer.src.experiment_environment import ExperimentEnvironment


class Experiment:
    def __init__(
            self,
            config : Config,
            name: str,
            target_branch: str,
            critical_services: List[str],
            env: ExperimentEnvironment,
            colocated_workload: bool = False,
            autoscaling: ScalingExperimentSetting = None,
            max_autoscale: int = 3,
    ):
        clue_config = config.clue_config
        sut_config = config.sut_config
        # metadata
        self.config = config
        self.name = name
        self.target_branch = target_branch
        self.namespace = sut_config.namespace
        self.infrastructure_namespaces = sut_config.infrastructure_namespaces
        self.critical_services = critical_services
        self.target_host = sut_config.target_host

        # observability data
        self.prometheus = clue_config.prometheus_url
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

    def __deepcopy__(self, memo=None):
        """
        Custom deepcopy method to ensure that the Experiment class is copied correctly. 
        """
        # Create a new instance of the class
        new_instance = Experiment(
            config=self.config,
            name=self.name,
            target_branch=self.target_branch,
            critical_services=self.critical_services,
            env=self.env,
            colocated_workload=self.colocated_workload,
            autoscaling=self.autoscaling,
            max_autoscale=self.max_autoscale,
        )
        return new_instance

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