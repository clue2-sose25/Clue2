from pydantic import BaseModel
from typing import List
from pathlib import Path
import yaml


class Experiment(BaseModel):
    name: str
    target_branch: str
    colocated_workload: bool


class ExperimentsConfig(BaseModel):
    experiments: List[Experiment]

    @classmethod
    def load_from_yaml(cls, config_path: Path) -> "ExperimentsConfig":
        """
        Load experiments configuration from a YAML file.
        """
        with open(config_path, 'r') as file:
            data = yaml.safe_load(file)
            return cls(**data)