from pydantic import BaseModel
from clue_deployer.src.models.sut import Sut


class SutsResponse(BaseModel):
    """
    A list of all available SUTs
    """
    suts: list[Sut]