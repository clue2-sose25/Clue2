from pydantic import BaseModel


class ExperimentEntry(BaseModel):
    """Single experiment entry with optional description"""

    name: str
    description: str | None = None


class Sut(BaseModel):
    '''
    A single SUT object, correlated to one SUT config file. 
    Contains the name and the experiments list of the SUT.
    '''
    name: str
    experiments: list[ExperimentEntry]
