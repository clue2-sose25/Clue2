from pydantic import BaseModel
from clue_deployer.service.status import Phase


class StatusOut(BaseModel):
    phase: Phase
    message: str | None = None