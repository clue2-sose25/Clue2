import os
import logging

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from clue_deployer.src import main
from clue_deployer.src.config import SUTConfig
from clue_deployer.service.status_manager import StatusManager, Phase

app = FastAPI(title="CLUE Deployer Service")

# Setup für Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ENV test
for var in ["SUT_NAME", "EXPERIMENT_NAME"]:
    if not os.getenv(var):
        logger.warning(f"⚠️ ENV-Variable {var} is not setted .")

logger.info(f"SUT={os.getenv('SUT_NAME')}, EXPERIMENT={os.getenv('EXPERIMENT_NAME')}")

SUT_CONFIGS_DIR = os.getenv("SUT_CONFIGS_PATH", "/app/sut_configs")
RESULTS_DIR = os.getenv("RESULTS_PATH", "/app/data")

class HealthResponse(BaseModel):
    message: str

class StringListResponse(BaseModel):
    strings: list[str]

class SutListResponse(BaseModel):
    suts: list[str]

class ExperimentListResponse(BaseModel):
    experiments: list[str]


class Result(BaseModel):
    timestamp: str
    workload: str
    branch_name: str
    experiment_number: int

class ResultListResponse(BaseModel):
    results: list[Result]
    
class StatusOut(BaseModel):
    phase: Phase
    message: str | None = None
 
@app.get("/status", response_model=StatusOut)
def read_status():
    phase, msg = StatusManager.get()
    return StatusOut(phase=phase, message=msg or None)

@app.get("/health")
async def root():
    return HealthResponse(message="Hello I am the Clue Deployer Service!")

@app.get("/list/sut", response_model=SutListResponse)
async def list_sut():
    """List all SUTs."""
    try:
        if not os.path.isdir(SUT_CONFIGS_DIR):
            raise HTTPException(status_code=404, detail=f"SUT configurations directory not found: {SUT_CONFIGS_DIR}")
        suts = os.listdir(SUT_CONFIGS_DIR)
        suts = [s for s in suts if s.endswith(('.yaml', '.yml')) and os.path.isfile(os.path.join(SUT_CONFIGS_DIR, s))]
        return SutListResponse(suts=suts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing SUTs: {str(e)}")

@app.get("/list/experiments", response_model=SutListResponse)
async def list_experiments():
    """List all experiments."""
    try:
        experiments = [experiment.name for experiment in main.CONFIGS.experiments_config.experiments]
        return ExperimentListResponse(experiments=experiments)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing experiments: {str(e)}")

@app.get("/list/results", response_model=StringListResponse)
async def list_results():
    """List all result timestamps."""
    try:
        if not os.path.isdir(RESULTS_DIR):
            raise HTTPException(status_code=404, detail=f"Results directory not found: {RESULTS_DIR}")
        
        results = [subdir.strip() for subdir in os.listdir(RESULTS_DIR)]

        return ResultListResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing results: {str(e)}")

@app.get("/result/{timestamp}", response_model=ResultListResponse)
async def get_result(timestamp: str):
    """Get results for a specific timestamp."""
    cleaned_timestamp = timestamp.strip()
    result_path = os.path.join(RESULTS_DIR, cleaned_timestamp)
    if not os.path.isdir(result_path):
        raise HTTPException(status_code=404, detail=f"Results not found for timestamp: {timestamp}")
    
    try:
        results = []
        for workload in os.listdir(result_path):
            workload = workload.strip()
            workload_path = os.path.join(result_path, workload)
            for branch in os.listdir(workload_path):
                branch = branch.strip()
                branch_path = os.path.join(workload_path, branch)
                for exp_num in os.listdir(branch_path):
                    exp_num = exp_num.strip()
                    results.append(Result(
                        timestamp=cleaned_timestamp,
                        workload=workload,
                        branch_name=branch,
                        experiment_number=int(exp_num)
                    ))
        return ResultListResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while retrieving results: {str(e)}")

@app.get("/sut/{sut_name}", response_model=SUTConfig)
async def get_sut(sut_name: str):
    """Get a specific SUT configuration."""
    cleaned_sut_name = sut_name.strip().lower()
    sut_filename = f"{cleaned_sut_name}.yaml"
    sut_path = os.path.join(SUT_CONFIGS_DIR, sut_filename)
    if not os.path.isfile(sut_path):
        raise HTTPException(status_code=404, detail=f"SUT configuration not found: {sut_name}")
    try: 
        sut_config = SUTConfig.load_from_yaml(sut_path)
        return sut_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while retrieving SUT configuration: {str(e)}")




