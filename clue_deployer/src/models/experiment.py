from uuid import UUID
from dataclasses import dataclass
from clue_deployer.src.config.config import Config
from typing import List
from clue_deployer.src.models.variant import Variant

@dataclass
class Experiment:
    """
    A single experiment, the parent object,
    correlated with a single SUT, including several variants and runs.
    """
    id: UUID
    configs: Config
    sut: str
    workloads: List[str]
    variants: List[Variant]
    timestamp: str
    n_iterations: int
    deploy_only: bool