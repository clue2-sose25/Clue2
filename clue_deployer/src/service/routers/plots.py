from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from clue_deployer.src.configs.configs import ENV_CONFIG
from clue_deployer.src.models.experiment import Experiment

SUT_CONFIGS_DIR = ENV_CONFIG.SUT_CONFIGS_PATH
RESULTS_DIR = ENV_CONFIG.RESULTS_PATH
CLUE_CONFIG_PATH = ENV_CONFIG.CLUE_CONFIG_PATH

router = APIRouter()

# @router.get("/api/plots")
# async def list_plots(request: Experiment, iteration: int):
#     """List all available plots for a specific iteration."""
#     workload = request.workload
#     branch_name = request.branch_name
#     experiment_number = iteration
#     timestamp = request.timestamp

#     results_path = Path(RESULTS_DIR) / timestamp / workload / branch_name / str(experiment_number)
    
#     if not results_path.exists():
#         raise HTTPException(status_code=404, detail=f"No results found for the specified iteration: {results_path}")

#     supported_formats = ["*.png", "*.jpg", "*.jpeg", "*.svg"]
#     plots = []
#     for file_format in supported_formats:
#         plots.extend([file.name for file in results_path.glob(file_format)])
#     return {"plots": plots}

# @router.get("/api/plots/download")
# async def download_plot(request: Experiment):
#     """Download a specific plot for a given iteration."""
#     workload = request.workload
#     branch_name = request.branch_name
#     experiment_number = request.experiment_number
#     timestamp = request.timestamp
#     plot_filename = request.plot_filename
#     results_path = Path(RESULTS_DIR) / timestamp / workload / branch_name / str(experiment_number)
#     plot_path = results_path / plot_filename
#     if not plot_path.exists():
#         raise HTTPException(status_code=404, detail=f"Plot file not found: {plot_path}")
#     return StreamingResponse(
#         open(plot_path, "rb"),
#         media_type="application/octet-stream",
#         headers={"Content-Disposition": f"attachment; filename={plot_filename}"}
#     )