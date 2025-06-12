from pydantic import BaseModel


class LogsResponse(BaseModel):
    logs: str