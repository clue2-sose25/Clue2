from pydantic import BaseModel
from typing import Dict

class Workload(BaseModel):
    """
    Class for workloads, containing shared constants and configuration.
    """
    def __init__(
        self,
        name: str,
        timeout_duration: int,
        workload_settings: Dict
    ):
        # Basic parameters
        self.name = name
        self.timeout_duration = timeout_duration
        # Validate workload_settings using Pydantic
        self.workload_settings = workload_settings

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
        )