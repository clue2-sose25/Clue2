from pydantic import BaseModel
from clue_deployer.src.models.Sut import Sut


class SutListResponse(BaseModel):
    """
    A list of all available SUTs
    """
    suts: list[Sut]