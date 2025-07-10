from pathlib import Path
from pydantic_settings import BaseSettings
import yaml

class ClueConfig(BaseSettings):
    """
    Configuration class for CLUE
    """
    experiment_timeout: int
    prometheus_url: str
    local_public_ip: str
    local_port: int
    remote_platform_arch: str
    local_platform_arch: str
    docker_registry_address: str
    target_utilization: int
    
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