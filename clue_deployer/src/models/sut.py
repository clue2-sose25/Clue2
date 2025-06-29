from pydantic import BaseModel


class VariantEntry(BaseModel):
    """Single SUT variant entry with optional description"""

    name: str
    description: str | None = None


class Sut(BaseModel):
    '''
    A single SUT object, correlated to one SUT config file. 
    Contains the name and the variants list of the SUT.
    '''
    name: str
    variants: list[VariantEntry]
