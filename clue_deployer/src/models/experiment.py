from uuid import UUID
from dataclasses import dataclass
from clue_deployer.src.configs.configs import Configs
from typing import List
from clue_deployer.src.models.workload import Workload
from clue_deployer.src.models.variant import Variant

@dataclass
class Experiment:
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