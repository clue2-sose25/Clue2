import json
from uuid import UUID
from pydantic import BaseModel
from typing import List
from clue_deployer.src.models.workload import Workload
from clue_deployer.src.models.variant import Variant
from clue_deployer.src.configs.configs import Configs



class Experiment(BaseModel):
    """
    A single experiment, the parent object,
    correlated with a single SUT, including several variants and runs.
    """
    id: UUID
    configs: Configs
    sut: str
    workloads: List[Workload]
    variants: List[Variant]
    timestamp: str
    n_iterations: int
    deploy_only: bool
    
    def to_json(self) -> str:
        """Return a JSON string representation of the experiment."""
        experiment_dict = {
            "id": str(self.id),
            "sut": self.sut,
            "workloads": [w.model_dump() for w in self.workloads],
            "variants": [v.model_dump() for v in self.variants],
            "timestamp": self.timestamp,
            "n_iterations": self.n_iterations,
            "deploy_only": self.deploy_only,
            "configs": self.configs.model_dump()
        }
        return json.dumps(experiment_dict, indent=2)
    
    def __str__(self) -> str:
        """Return a readable string representation of the experiment."""
        workload_strs = [str(w) for w in self.workloads]
        variant_strs = [str(v) for v in self.variants]
        
        return (
            f"Experiment(id={str(self.id)[:8]}..., "
            f"sut='{self.sut}', "
            f"workloads={workload_strs}, "
            f"variants={variant_strs}, "
            f"timestamp='{self.timestamp}', "
            f"iterations={self.n_iterations}, "
            f"deploy_only={self.deploy_only})"
        )