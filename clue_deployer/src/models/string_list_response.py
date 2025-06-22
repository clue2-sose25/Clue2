from pydantic import BaseModel


class StringListResponse(BaseModel):
    strings: list[str]