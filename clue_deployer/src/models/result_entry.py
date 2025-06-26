from uuid import UUID
from pydantic import BaseModel

class ResultEntry(BaseModel):
    """
    A single results folder object
    """
    id: UUID
    sut: str
    workloads: list[str]
    variants: list[str]
    timestamp: str
    n_iterations: int