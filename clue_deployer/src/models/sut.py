from pydantic import BaseModel


class Sut(BaseModel):
    '''
    A single SUT object, correlated to one SUT config file. 
    Contains the name and the experiments list of the SUT.
    '''
    name: str
    experiments: list[str]
