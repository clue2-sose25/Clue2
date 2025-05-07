from cfgload import load_config
from pydantic import BaseModel
from pathlib import Path
from config import SUTConfig, ClueConfig, ServicesConfig

from experiment_workloads import Workload

#not really necessary anymore
# class WorkloadAutoConfig(Protocol):
#     def set_workload(self, exp:"ExperimentEnvironment"):
#         pass

CONFIG_PATH = Path("..").joinpath("cfg").joinpath("experiment_config.yaml")


class EnvironmentConfig(BaseModel):
    sut_path: str
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
    def __init__(self, sut_config: SUTConfig,
                 clue_config: ClueConfig,
                 services_config: ServicesConfig):
        """
        Initialize the ExperimentEnvironment with an EnvironmentConfig instance.
        """
        #self.config = config

        # Files / IO
        self.sut_path = sut_config.sut_path
        self.local_public_ip = clue_config.local_public_ip

        # Infra
        self.docker_user = clue_config.docker_user
        self.local_port = clue_config.local_port
        self.remote_platform_arch = clue_config.remote_platform_arch
        self.local_platform_arch = clue_config.local_platform_arch
        self.resource_limits = services_config.get_all_resource_limits()
        self.default_resource_limits = sut_config.default_resource_limits
        self.workload_settings = sut_config.workload_settings
        self.timeout_duration = sut_config.timeout_duration
        self.wait_before_workloads = sut_config.wait_before_workloads
        self.wait_after_workloads = sut_config.wait_after_workloads
        self.tags = sut_config.tags
        self.kind_cluster_name = None #TODO
    

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
    