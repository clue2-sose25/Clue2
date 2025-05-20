from pydantic import BaseModel
from pathlib import Path
import yaml

#TODO use defaults
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
    
    def get_all_resource_limits(self) -> dict[str, dict[str, int]]:
        """
        Get all resource limits for all services in the format needed
        """
        return {service.name: service.resource_limits for service in self.services}

