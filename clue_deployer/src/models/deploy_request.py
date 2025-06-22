from pydantic import BaseModel


class DeployRequest(BaseModel):
    experiment_name: str
    sut_name: str
    n_iterations: int = 1   
    deploy_only: bool = False
