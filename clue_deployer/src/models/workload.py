from pydantic import BaseModel
from typing import Dict

class Workload(BaseModel):
    """
    A simple class for workloads loaded from SUT config yaml
    """
    name: str
    description: str
    timeout_duration: int
    workload_settings: Dict
    locust_files: list[str]

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"