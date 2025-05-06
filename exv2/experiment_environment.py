from cfgload import load_config
from pydantic import BaseModel
from pathlib import Path

from experiment_workloads import Workload

#not really necessary anymore
# class WorkloadAutoConfig(Protocol):
#     def set_workload(self, exp:"ExperimentEnvironment"):
#         pass

CONFIG_PATH = Path("..").joinpath("cfg").joinpath("experiment_config.yaml")


class EnvironmentConfig(BaseModel):
    docker_user: str
    local_public_ip: str
    local_port: int
    remote_platform_arch: str
    local_platform_arch: str
    resource_limits: dict[str, dict[str, int]]
    default_resource_limits: dict[str, int]
    workload_settings: dict[str, str]
    timeout_duration: int
    wait_before_workloads: int
    wait_after_workloads: int
    tags: list[str]

    @classmethod
    def load_from_yaml(cls, config_path: str) -> "EnvironmentConfig":
        """
        Load environment configuration from a YAML file.
        """
        with open(config_path, 'r') as file:
            cfg = load_config()
            return cls(**cfg)



class ExperimentEnvironment:
    def __init__(self, config: EnvironmentConfig):
        """
        Initialize the ExperimentEnvironment with an EnvironmentConfig instance.
        """
        self.config = config

        # Files / IO
        self.teastore_path = "teastore"  # Default path for the teastore repo
        self.local_public_ip = config.local_public_ip

        # Infra
        self.docker_user = config.docker_user
        self.local_port = config.local_port
        self.remote_platform_arch = config.remote_platform_arch
        self.local_platform_arch = config.local_platform_arch
        self.resource_limits = config.resource_limits
        self.default_resource_limits = config.default_resource_limits
        self.workload_settings = config.workload_settings
        self.timeout_duration = config.timeout_duration
        self.wait_before_workloads = config.wait_before_workloads
        self.wait_after_workloads = config.wait_after_workloads
        self.tags = config.tags
        self.kind_cluster_name = None
    
    @staticmethod
    def from_config(config_path: str = CONFIG_PATH) -> "ExperimentEnvironment":
        """
        Create an ExperimentEnvironment instance from a YAML configuration file.
        """
        config = EnvironmentConfig.load_from_yaml(config_path)
        return ExperimentEnvironment(config)
    
    def __repr__(self):
        return f"ExperimentEnvironment({self.config})"

    def total_duration(self) -> int:
        """
        Calculate the total duration of the experiment.
        """
        return self.timeout_duration + 30  # Add a buffer of 30 seconds

    def set_workload(self, workload):
        """
        Set the workload for the experiment.
        """
        workload.set_workload(self)
    
    def total_duration(self):
        return self.timeout_duration + 30 #TODO make this more sensable but not based on the worklaod settings

    def set_workload(self, conf: Workload):
        conf.set_workload(self)
    