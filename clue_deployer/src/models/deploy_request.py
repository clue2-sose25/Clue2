from pydantic import BaseModel, Field


class DeployRequest(BaseModel):
    variants: list[str]
    workloads: list[str]
    sut: str
    n_iterations: int = 1   
    deploy_only: bool = False
    workloads: list[str] = []