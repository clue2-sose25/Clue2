import os
import logging
import zipfile
import io
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from pathlib import Path
from clue_deployer.src.config.config import ENV_CONFIG
from clue_deployer.src.main import ClueRunner
from clue_deployer.src.config import SUTConfig, Config
from clue_deployer.service.status_manager import StatusManager
from clue_deployer.service.models import (
    HealthResponse,
    SutListResponse,
    ExperimentListResponse,
    Timestamp,
    Iteration,
    ResultTimestampResponse,
    DeployRequest,
    StatusOut,
    LogsResponse
)

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
        logger.warning(f"⚠️ ENV-Variable {var} is not set .")

logger.info(f"SUT={os.getenv('SUT_NAME')}, EXPERIMENT={os.getenv('EXPERIMENT_NAME')}")

SUT_CONFIGS_DIR = ENV_CONFIG.SUT_CONFIGS_PATH
RESULTS_DIR = ENV_CONFIG.RESULTS_PATH
CLUE_CONFIG_PATH = ENV_CONFIG.CLUE_CONFIG_PATH
# Use a relative path so it aligns with the logger configuration
LOG_FILE_PATH = Path("logs/app.log")

 
@app.get("/status", response_model=StatusOut)
def read_status():
    phase, msg = StatusManager.get()
    return StatusOut(phase=phase, message=msg or None)

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(message="true")

@app.get("/", response_model=None)
async def root():
    return RedirectResponse(url="/docs")  # Redirect to /docs

@app.get("/api/logs", response_model=LogsResponse)
def read_logs():

    """Return buffered log lines."""
    return LogsResponse(logs="\n".join(LOG_BUFFER))
#    """Return contents of the deployer log file."""
#    try:
#        if LOG_FILE_PATH.exists():
#            content = LOG_FILE_PATH.read_text()
#        else:
#            content = ""
#        return LogsResponse(logs=content)
#    except Exception as e:
#        logger.exception("Failed to read log file")
#        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs/stream")
async def stream_logs():
    """Stream log buffer updates using Server-Sent Events."""
    async def event_generator():
        last_idx = len(LOG_BUFFER)
        while True:
            if len(LOG_BUFFER) > last_idx:
                for line in list(LOG_BUFFER)[last_idx:]:
                    yield f"data: {line}\n\n"
                last_idx = len(LOG_BUFFER)
            else:
                await asyncio.sleep(1)
#    """Stream log file updates using Server-Sent Events."""
#    async def event_generator():
#        # Wait until log file exists
#        while not LOG_FILE_PATH.exists():
#            await asyncio.sleep(1)
#        with LOG_FILE_PATH.open("r") as f:
#            f.seek(0, os.SEEK_END)
#            while True:
#                line = f.readline()
#                if line:
#                    yield f"data: {line}\n\n"
#                else:
#                    await asyncio.sleep(1)
#
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/list/sut", response_model=SutListResponse)
async def list_sut():
    """List all SUTs."""
    try:
        if not os.path.isdir(SUT_CONFIGS_DIR):
            raise HTTPException(status_code=404, detail=f"SUT configurations directory not found: {SUT_CONFIGS_DIR}")
        suts = os.listdir(SUT_CONFIGS_DIR)
        suts = [s for s in suts if s.endswith(('.yaml', '.yml')) and os.path.isfile(os.path.join(SUT_CONFIGS_DIR, s))]
        suts = [os.path.splitext(s)[0] for s in suts]
        return SutListResponse(suts=suts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing SUTs: {str(e)}")

@app.get("/list/experiments", response_model=ExperimentListResponse)
async def list_experiments():
    """List all experiemnt names"""
    try:
        experiments = [experiment.name for experiment in main.CONFIGS.experiments_config.experiments]
        return ExperimentListResponse(experiments=experiments)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing experiments: {str(e)}")

# @app.get("/list/results", response_model=ResultListResponse)
# async def list_results():
#     """List all result timestamps."""
#     try:
#         # if not os.path.isdir(RESULTS_DIR):
#         #     raise HTTPException(status_code=404, detail=f"Results directory not found: {RESULTS_DIR}")
#         if not os.path.exists(RESULTS_DIR):
#             return ResultListResponse(results=[])
        
#         results = [subdir.strip() for subdir in os.listdir(RESULTS_DIR)]

#         return ResultListResponse(results=results)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing results: {str(e)}")

@app.get("/list/results", response_model=ResultTimestampResponse) # Path suggests listing all
async def list_all_results(): # Renamed function for clarity
    """List all results, structured by timestamp, workload, branch, and experiment number."""
    results_base_path = Path(RESULTS_DIR) # Use pathlib

    if not results_base_path.is_dir():
        logger.error(f"Results directory not found: {results_base_path}")
        raise HTTPException(status_code=404, detail=f"Results directory not found: {results_base_path}")
    
    try:
        processed_timestamps = [] # Renamed from 'results' to avoid confusion with response model field
        
        for timestamp_dir in results_base_path.iterdir(): # pathlib's way to list entries
            if not timestamp_dir.is_dir(): # Skip if not a directory
                logger.debug(f"Skipping non-directory entry in results: {timestamp_dir.name}")
                continue

            timestamp_data_obj = Timestamp(timestamp=timestamp_dir.name.strip(), iterations=[])
            
            for workload_dir in timestamp_dir.iterdir():
                if not workload_dir.is_dir():
                    logger.debug(f"Skipping non-directory entry in timestamp '{timestamp_dir.name}': {workload_dir.name}")
                    continue
                
                workload_name = workload_dir.name.strip()
                
                for branch_dir in workload_dir.iterdir():
                    if not branch_dir.is_dir():
                        logger.debug(f"Skipping non-directory entry in workload '{workload_name}': {branch_dir.name}")
                        continue
                    
                    branch_name_str = branch_dir.name.strip()
                    
                    for exp_num_dir in branch_dir.iterdir():
                        if not exp_num_dir.is_dir(): 
                            logger.debug(f"Skipping non-directory entry in branch '{branch_name_str}': {exp_num_dir.name}")
                            continue
                        
                        exp_num_str = exp_num_dir.name.strip()
                        try:
                            experiment_number_int = int(exp_num_str)
                            timestamp_data_obj.iterations.append(
                                Iteration(
                                    workload=workload_name,
                                    branch_name=branch_name_str,
                                    experiment_number=experiment_number_int
                                )
                            )
                        except ValueError:
                            logger.warning(f"Could not convert experiment number '{exp_num_str}' to int for {timestamp_dir.name}/{workload_name}/{branch_name_str}. Skipping.")
                            raise ValueError(f"experiment_number{experiment_number_int} cannot be casted into an integer.")
            
            processed_timestamps.append(timestamp_data_obj)
            
        return ResultTimestampResponse(results=processed_timestamps)
    except PermissionError:
        logger.exception("Permission error while accessing results directory.")
        raise HTTPException(status_code=500, detail="Permission denied when accessing results.")
    except Exception as e:
        logger.exception("Unexpected error while retrieving results.")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while retrieving results: {str(e)}")

@app.get("/download/results")
def download_results():
    """Download all results as a zip file."""
    results_path = Path(RESULTS_DIR)
    if not results_path.exists():
        raise HTTPException(status_code=404, detail=f"Results directory {results_path} does not exist.\
                             Did you run any experiments?")
    
    # Create an in-memory zip file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in results_path.rglob("*"):  # Recursively add all files
            if file_path.is_file():
                zip_file.write(file_path, file_path.relative_to(results_path))
    
    # Prepare the buffer for reading
    zip_buffer.seek(0)

    # Return the zip file as a streaming response
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=results_{results_path.name}.zip"}
    )

@app.get("/config/sut/{sut_name}", response_model=SUTConfig)
async def get_sut_config(sut_name: str):
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



@app.post("/deploy/sut")
def deploy_sut(request: DeployRequest):
    """Deploy a specific SUT."""
    sut_name = request.sut_name
    deploy_only = request.deploy_only
    experiment_name = request.experiment_name
    sut_filename = f"{sut_name}.yaml"
    sut_path = os.path.join(SUT_CONFIGS_DIR, sut_filename)
    
    if not os.path.isfile(sut_path):
        raise HTTPException(status_code=404, detail=f"SUT configuration not found: {request.sut_name}")
    
    config = Config(sut_config=sut_path, clue_config=CLUE_CONFIG_PATH)
    try:
        # run the clue main method
        runner = ClueRunner(config, experiment_name=experiment_name, sut_name=sut_name, deploy_only=deploy_only)
        runner.main()
        return {"message": f"SUT {request.sut_name} has been deployed successfully."}
    except Exception as e:
        logger.error(f"Failed to deploy SUT {request.sut_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to deploy SUT: {str(e)}")

    
    

