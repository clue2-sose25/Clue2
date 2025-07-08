from pydantic import BaseModel

class DeployRequest(BaseModel):
    variants: str
    workloads: str
    sut: str
    n_iterations: int = 1   
    deploy_only: bool = False
    workloads: list[str] = []