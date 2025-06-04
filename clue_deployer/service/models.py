
from pydantic import BaseModel

class HealthResponse(BaseModel):
    message: str

class StringListResponse(BaseModel):
    strings: list[str]

class SutListResponse(BaseModel):
    suts: list[str]

class ExperimentListResponse(BaseModel):
    experiments: list[str]


class Result(BaseModel):
    timestamp: str
    workload: str
    branch_name: str
    experiment_number: int

class ResultsResponse(BaseModel):
    results: list[Result]

class ResultListResponse(BaseModel):
    results: list[str]    
class StatusOut(BaseModel):
    phase: Phase
    message: str | None = None