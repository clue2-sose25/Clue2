from pathlib import Path
from pydantic import BaseModel


class PlotRequest(BaseModel):
    workload: str
    branch_name: str
    experiment_number: int
    timestamp: str
    plot_name: Path