from uuid import UUID
from pydantic import BaseModel
from clue_deployer.src.config.config import Config

class Experiment(BaseModel):
    """
    A single experiment, the parent object,
    correlated with a single SUT, including several variants and runs.
    """
    id: UUID
    configs: Config
    sut: str
    workloads: list[str]
    variants: list[str]
    timestamp: str
    n_iterations: int
    deploy_only: bool