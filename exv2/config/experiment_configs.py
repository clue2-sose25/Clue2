from pydantic import BaseModel, Field
from typing import List
from pathlib import Path
import yaml


class SingleExperiment(BaseModel):
    name: str
    target_branch: str
    colocated_workload: bool
    critical_services= Field(default_factory=list) #default empty list if not provided


class ExperimentsConfig(BaseModel):
    experiments: List[SingleExperiment]

    @classmethod
    def load_from_yaml(cls, config_path: Path) -> "ExperimentsConfig":
        """
        Load experiments configuration from a YAML file.
        """
        with open(config_path, 'r') as file:
            data = yaml.safe_load(file)
            return cls(**data)