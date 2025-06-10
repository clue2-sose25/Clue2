from pathlib import Path


from pydantic import BaseModel

from clue_deployer.service.status import Phase

class HealthResponse(BaseModel):
    message: str

class StringListResponse(BaseModel):
    strings: list[str]

class Sut(BaseModel):
    '''
    A single SUT object, correlated to one SUT config file. 
    Contains the name and the experiments list of the SUT.
    '''
    name: str
    experiments: list[str]

class SutListResponse(BaseModel):
    """
    A list of all available SUTs
    """
    suts: list[Sut]

class ExperimentListResponse(BaseModel):
    experiments: list[str]

class Iteration(BaseModel):
    workload: str
    branch_name: str
    experiment_number: int

class Timestamp(BaseModel):
    timestamp: str
    iterations: list[Iteration]

class SingleIteration(BaseModel):
    workload: str
    branch_name: str
    experiment_number: int
    timestamp: str

class PlotRequest(BaseModel):
    workload: str
    branch_name: str
    experiment_number: int
    timestamp: str
    plot_name: Path

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
    n_iterations: int = 1   
    deploy_only: bool = False

