from pydantic import BaseModel


class StartServerRequest(BaseModel):
    uuid: str
    sut_name: str