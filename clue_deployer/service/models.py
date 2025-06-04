from pydantic import BaseModel

from clue_deployer.service.status import Phase

class HealthResponse(BaseModel):
    message: str

class StringListResponse(BaseModel):
    strings: list[str]

class SutListResponse(BaseModel):
    suts: list[str]

class ExperimentListResponse(BaseModel):
    experiments: list[str]

class Iteration(BaseModel):
    workload: str
    branch_name: str
    experiment_number: int

class Timestamp(BaseModel):
    timestamp: str
    iterations: list[Iteration]

class ResultTimestampResponse(BaseModel):
    results: list[Timestamp]

class ResultListResponse(BaseModel):
    results: list[str]    
class StatusOut(BaseModel):
    phase: Phase
    message: str | None = None

class DeployRequest(BaseModel):
    experiment_name: str
    sut_name: str