from pydantic import BaseModel
from clue_deployer.src.models.ResultEntry import ResultEntry

class ResultsResponse(BaseModel):
    """
    A response for the /list/results endpoint
    """
    results: list[ResultEntry]