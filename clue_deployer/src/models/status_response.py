from pydantic import BaseModel
from clue_deployer.src.models.status_phase import StatusPhase


class StatusResponse(BaseModel):
    phase: StatusPhase
    message: str | None = None