from pathlib import Path
from clue_deployer.src.configs import Configs

CONFIG_PATH = Path("..").joinpath("cfg").joinpath("experiment_config.yaml")

class VariantEnvironment:
    def __init__(self, config: Configs):
        """
        Initialize the ExperimentEnvironment instance
        """
        sut_config = config.sut_config
        clue_config = config.clue_config
        services_config = config.services_config
        # Files / IO
        self.sut_path = sut_config.sut_path
        self.local_public_ip = clue_config.local_public_ip
        # Infra
        self.local_port = clue_config.local_port
        self.docker_registry_address = clue_config.docker_registry_address
        self.remote_platform_arch = clue_config.remote_platform_arch
        self.local_platform_arch = clue_config.local_platform_arch
        self.resource_limits = services_config.get_all_resource_limits()
        self.default_resource_limits = sut_config.default_resource_limits
        self.wait_before_workloads = sut_config.wait_before_workloads
        self.wait_after_workloads = sut_config.wait_after_workloads