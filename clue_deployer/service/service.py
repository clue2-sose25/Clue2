import os
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from clue_deployer import main
from clue_deployer.config import Config, SutConfig, ClueConfig

app = FastAPI()

SUT_CONFIGS_DIR = os.getenv("SUT_CONFIGS_PATH", "/app/sut_configs")
RESULTS_DIR = os.getenv("RESULTS_PATH", "/app/results")

class HealthResponse(BaseModel):
    message: str

class StringListResponse(BaseModel):
    strings: list[str]

class Result(BaseModel):
    timestamp: str
    workload: str
    branch_name: str
    experiment_number: int

class ResultListResponse(BaseModel):
    results: list[Result]

@app.get("/health")
async def root():
    return HealthResponse(message="Hello I am the Clue Deployer Service!")

@app.get("/list/sut", response_model=StringListResponse)
async def list_sut():
    """List all SUTs."""
    try:
        if not os.path.isdir(SUT_CONFIGS_DIR):
            raise HTTPException(status_code=404, detail=f"SUT configurations directory not found: {SUT_CONFIGS_DIR}")
        suts = os.listdir(SUT_CONFIGS_DIR)
        suts = [s for s in suts if s.endswith(('.yaml', '.yml')) and os.path.isfile(os.path.join(SUT_CONFIGS_DIR, s))]
        return StringListResponse(suts=suts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing SUTs: {str(e)}")

@app.get("list/experiments", response_model=StringListResponse)
async def list_experiments():
    """List all experiments."""
    try:
        experiments = [experiment.name for experiment in main.CONFIGS.experiment_configs.exporiments]
        return StringListResponse(experiments=experiments)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing experiments: {str(e)}")

@app.get("list/results", StringListResponse)
async def list_results():
    """List all results."""
    try:
        if not os.path.isdir(RESULTS_DIR):
            raise HTTPException(status_code=404, detail=f"Results directory not found: {RESULTS_DIR}")
        for subdir in os.listdir(RESULTS_DIR):
            pass  # Ensure the subdirectory is a directory
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing results: {str(e)}")


@app.get("/sut/{sut_name}", response_model=SutConfig)
async def get_sut(sut_name: str):
    """Get a specific SUT configuration."""
    cleaned_sut_name = sut_name.strip().lower()
    sut_filename = f"{cleaned_sut_name}.yaml"
    sut_path = os.path.join(SUT_CONFIGS_DIR, sut_filename)
    if not os.path.isfile(sut_path):
        raise HTTPException(status_code=404, detail=f"SUT configuration not found: {sut_name}")
    try: 
        sut_config = SutConfig.load_from_yaml(sut_path)
        return sut_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while retrieving SUT configuration: {str(e)}")




