from pydantic import BaseModel


class Service(BaseModel):
    name: str
    resource_limits: dict[str, int]