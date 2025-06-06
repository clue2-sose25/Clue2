from pydantic_settings import BaseSettings
from pathlib import Path
import yaml



class ClueConfig(BaseSettings):
    """
    Configuration class for CLUE using pydantic's BaseSettings.
    """
    prometheus_url: str
    local_public_ip: str
    local_port: int
    remote_platform_arch: str
    local_platform_arch: str
    docker_registry_address: str
    result_base_path: Path
    workloads: list[str] 
    target_utilization: str

    class Config:
        # Allow environment variable overrides
        env_prefix = "CLUE_"

    @classmethod
    def load_from_yaml(cls, config_path: Path) -> "ClueConfig":
        """
        Load configuration from a YAML file.
        """
        with open(config_path, 'r') as file:
            data = yaml.safe_load(file).get('config', {})
            return cls(**data)