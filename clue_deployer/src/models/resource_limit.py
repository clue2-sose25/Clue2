from pydantic import BaseModel


class ResourceLimit(BaseModel):
    service_name: str
    limit: dict[str, int]