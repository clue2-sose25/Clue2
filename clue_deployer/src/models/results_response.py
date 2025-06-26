from pydantic import BaseModel
from clue_deployer.src.models.experiment import Experiment

class ResultsResponse(BaseModel):
    """
    A response for the /list/results endpoint
    """
    results: list[Experiment]