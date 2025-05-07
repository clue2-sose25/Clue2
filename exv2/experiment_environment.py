from pathlib import Path
from config import SUTConfig, ClueConfig, ServicesConfig

from experiment_workloads import Workload


CONFIG_PATH = Path("..").joinpath("cfg").joinpath("experiment_config.yaml")

class ExperimentEnvironment:
    def __init__(self, sut_config: SUTConfig,
                 clue_config: ClueConfig,
                 services_config: ServicesConfig):
        """
        Initialize the ExperimentEnvironment Instance.
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
    