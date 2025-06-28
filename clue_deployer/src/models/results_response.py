from pydantic import BaseModel
from clue_deployer.src.models.result_entry import ResultEntry

class ResultsResponse(BaseModel):
    """
    A response for the /list/results endpoint
    """
    results: list[ResultEntry]