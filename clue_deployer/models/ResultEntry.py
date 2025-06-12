from pydantic import BaseModel

class ResultEntry(BaseModel):
    """
    A single results folder object
    """
    id: str
    workload: str
    branch_name: str
    experiment_number: int
    timestamp: str
    iterations: int