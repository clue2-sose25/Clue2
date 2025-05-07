from pydantic import BaseSettings, Field
from pathlib import Path
import yaml

# Global constant for the YAML configuration file path
  


class SUTConfig(BaseSettings):
    """
    Configuration class for the System Under Test (SUT) using pydantic's BaseSettings.
    """
    namespace: str
    target_host: str
    default_resource_limits: dict[str, int]
    workload_settings: dict[str, str]
    timeout_duration: int
    wait_before_workloads: int
    wait_after_workloads: int
    tags: list[str]
    infrastructure_namespaces: list[str] = Field(default_factory=list)  

    class Config:
        # Allow environment variable overrides
        env_prefix = "SUT_"

    @classmethod
    def load_from_yaml(cls, sut_config_path) -> "SUTConfig":
        """
        Load configuration from the YAML file specified by the global SUT_CONFIG_PATH.
        """
        with open(sut_config_path, 'r') as file:
            data = yaml.safe_load(file).get('config', {})
            return cls(**data)
