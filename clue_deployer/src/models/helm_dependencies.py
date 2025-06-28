import yaml
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path


class Dependency(BaseModel):
    name: str
    version: str
    repository: str
    condition: Optional[str] = None  # Optional field for conditions


class Dependencies(BaseModel):
    dependencies: List[Dependency]

    @classmethod
    def load_from_yaml(cls, char_path: Path) -> "Dependencies":
        """
        Load experiments configuration from a YAML file.
        """
        with open(char_path, 'r') as file:
            data = yaml.safe_load(file)
            return cls(**data)