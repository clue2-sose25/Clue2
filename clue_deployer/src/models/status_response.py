from pydantic import BaseModel
from clue_deployer.src.models.status_phase import StatusPhase


class StatusResponse(BaseModel):
    is_deploying: bool 
    phase: StatusPhase | None
    message: str | None = None