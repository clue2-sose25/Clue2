from pydantic import BaseModel
from pathlib import Path
import yaml


class Service(BaseModel):
    name: str
    resource_limits: dict[str, int]


class ServicesConfig(BaseModel):
    services: list[Service]

    @classmethod
    def load_from_yaml(cls, config_path: Path) -> "ServicesConfig":
        """
        Load services configuration from a YAML file.
        """
        with open(config_path, 'r') as file:
            data = yaml.safe_load(file)
            return cls(**data)

