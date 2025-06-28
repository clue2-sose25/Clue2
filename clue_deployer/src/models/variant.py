from typing import List
import json
from pydantic import BaseModel
from clue_deployer.src.models.scaling_experiment_setting import ScalingExperimentSetting

class Variant(BaseModel):
    """
    Variant configuration model
    """
    name: str
    target_branch: str
    critical_services: List[str]
    colocated_workload: bool = False
    autoscaling: ScalingExperimentSetting = "cpu"
    max_autoscale: int = 3
    description: str = ""

    def __str__(self) -> str:
        return self.name

    def create_json(self) -> str:
        description = {
            "name": self.name,
            "target_branch": self.target_branch,
            "executor": "colocated" if self.colocated_workload else "local",
            "scaling": str(self.autoscaling),
            "max_autoscale": str(self.max_autoscale),
            "critical_services": self.critical_services
        }
        return json.dumps(description)