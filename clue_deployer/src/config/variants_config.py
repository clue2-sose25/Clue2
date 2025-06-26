from pydantic import BaseModel, Field
from typing import List
from pathlib import Path
import yaml


class Variant(BaseModel):
    name: str
    description: str | None = None
    target_branch: str
    colocated_workload: bool = Field(default=False)
    critical_services: list[str] = Field(default_factory=list)  # default empty list if not provided
    autoscaling: str


class VariantsConfig(BaseModel):
    # The list of variants for the SUT
    variants: List[Variant]

    @classmethod
    def load_from_yaml(cls, config_path: Path) -> "VariantsConfig":
        """
        Load experiments configuration from a YAML file.
        """
        with open(config_path, 'r') as file:
            data = yaml.safe_load(file)
            return cls(**data)