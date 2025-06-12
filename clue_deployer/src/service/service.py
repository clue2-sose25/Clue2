import os
import zipfile
import io
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse, RedirectResponse
from pathlib import Path
import yaml
import multiprocessing
from clue_deployer.src.models.logs_response import LogsResponse
from clue_deployer.src.models.result_entry import ResultEntry
from clue_deployer.src.models.deploy_request import DeployRequest
from clue_deployer.src.models.health_response import HealthResponse
from clue_deployer.src.models.results_response import ResultsResponse
from clue_deployer.src.models.status_response import StatusResponse
from clue_deployer.src.models.sut import Sut
from clue_deployer.src.models.suts_response import SutsResponse
from clue_deployer.src.service.status_manager import StatusManager
from clue_deployer.src.logger import logger
from clue_deployer.src.config.config import ENV_CONFIG
from clue_deployer.src.logger import LOG_BUFFER
from clue_deployer.src.main import ClueRunner
from clue_deployer.src.config import SUTConfig, Config

# Initialize multiprocessing lock and value for deployment synchronization. Used for deployments.
state_lock = multiprocessing.Lock()
is_deploying = multiprocessing.Value('i', 0)

# Root page redirect to swagger /docs
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic: Add redirect from / to /docs
    from starlette.routing import Route
    async def redirect_to_docs(request):
        return RedirectResponse(url="/docs")
    app.router.routes.insert(0, Route("/", endpoint=redirect_to_docs, methods=["GET"]))
    yield  # Yield control to the application

# Start the FastAPI server
app = FastAPI(title="CLUE Deployer Service", lifespan=lifespan)

SUT_CONFIGS_DIR = ENV_CONFIG.SUT_CONFIGS_PATH
RESULTS_DIR = ENV_CONFIG.RESULTS_PATH
CLUE_CONFIG_PATH = ENV_CONFIG.CLUE_CONFIG_PATH

def run_deployment(config, experiment_name, sut_name, deploy_only, n_iterations, state_lock, is_deploying):
    """Function to run the deployment in a separate process."""
    try:
        runner = ClueRunner(config, experiment_name=experiment_name, sut_name=sut_name, deploy_only=deploy_only, n_iterations=n_iterations)
        runner.main()
    except Exception as e:
        logger.error(f"Deployment process failed for SUT {sut_name}: {str(e)}")
    finally:
        with state_lock:
            is_deploying.value = 0

@app.get("/api/status", response_model=StatusResponse)
def read_status():
    phase, msg = StatusManager.get()
    return StatusResponse(phase=phase, message=msg or None)

@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(message="true")

@app.get("/api/logs", response_model=LogsResponse)
def read_logs():

    """Return buffered log lines."""
    return LogsResponse(logs="\n".join(LOG_BUFFER))

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
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/list/sut", response_model=SutsResponse)
async def list_sut():
    """
    List all SUTs with their experiments.
    """
    try:
        if not os.path.isdir(SUT_CONFIGS_DIR):
            raise HTTPException(status_code=404, detail=f"SUT configurations directory not found: {SUT_CONFIGS_DIR}")

        # Get list of YAML files in the SUT configurations directory
        files = [f for f in os.listdir(SUT_CONFIGS_DIR) if f.endswith(('.yaml', '.yml')) and os.path.isfile(os.path.join(SUT_CONFIGS_DIR, f))]

        suts = []
        for filename in files:
            # Extract SUT name from filename (without extension)
            sut_name = os.path.splitext(filename)[0]
            file_path = os.path.join(SUT_CONFIGS_DIR, filename)

            # Read and parse the YAML file
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)

            # Validate that the YAML content is a dictionary
            if not isinstance(data, dict):
                raise HTTPException(status_code=500, detail=f"Invalid SUT configuration file: {filename} is not a valid YAML dictionary")

            # Get experiments section, default to empty list if missing
            experiments = data.get('experiments', [])
            if not isinstance(experiments, list):
                raise HTTPException(status_code=500, detail=f"Invalid SUT configuration file: {filename} has 'experiments' that is not a list")

            # Extract experiment names
            experiment_names = []
            for exp in experiments:
                if not isinstance(exp, dict) or 'name' not in exp:
                    raise HTTPException(status_code=500, detail=f"Invalid experiment in SUT configuration file: {filename}")
                experiment_names.append(exp['name'])

            # Create Sut object and add to list
            sut = Sut(name=sut_name, experiments=experiment_names)
            suts.append(sut)

        return SutsResponse(suts=suts)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing SUTs: {str(e)}")

@app.get("/api/results", response_model=ResultsResponse)
async def list_all_results():
    """List all results, structured by timestamp, workload, branch, and experiment number."""
    results_base_path = Path(RESULTS_DIR)
    # Check for results directory
    if not results_base_path.is_dir():
        logger.error(f"Results directory not found: {results_base_path}")
        raise HTTPException(status_code=404, detail=f"Results directory not found: {results_base_path}")
    # List the results
    try:
        processed_results = []
        
        for results_dir in results_base_path.iterdir():
            if not results_dir.is_dir():
                logger.debug(f"Skipping non-directory entry in results: {results_dir.name}")
                continue

            timestamp = results_dir.name.strip()
            
            for workload_dir in results_dir.iterdir():
                if not workload_dir.is_dir():
                    logger.debug(f"Skipping non-directory entry in timestamp '{results_dir.name}': {workload_dir.name}")
                    continue
                
                workload_name = workload_dir.name.strip()
                
                for branch_dir in workload_dir.iterdir():
                    if not branch_dir.is_dir():
                        logger.debug(f"Skipping non-directory entry in workload '{workload_name}': {branch_dir.name}")
                        continue
                    
                    branch_name_str = branch_dir.name.strip()
                    # Count the iterations
                    iterations_count = 0
                    for exp_num_dir in branch_dir.iterdir():
                        if not exp_num_dir.is_dir():
                            logger.debug(f"Skipping non-directory entry in branch '{branch_name_str}': {exp_num_dir.name}")
                            continue              
                        # Count iterations in the experiment directory
                        iterations_count = iterations_count + 1
                    # Generate a unique ID for this result entry
                    result_id = f"{timestamp}_{workload_name}_{branch_name_str}"
                    # Append the results
                    processed_results.append(
                        ResultEntry(
                            id=result_id,
                            workload=workload_name,
                            branch_name=branch_name_str,
                            timestamp=timestamp,
                            iterations=iterations_count
                        )
                    )
        return ResultsResponse(results=processed_results)
    except PermissionError:
        logger.exception("Permission error while accessing results directory.")
        raise HTTPException(status_code=500, detail="Permission denied when accessing results.")
    except Exception as e:
        logger.exception("Unexpected error while retrieving results.")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while retrieving results: {str(e)}")

@app.get("/api/results/{result_id}", response_model=ResultEntry)
async def get_single_result(result_id: str):
    """Get a single result by ID."""
    results_base_path = Path(RESULTS_DIR)
    
    # Check for results directory
    if not results_base_path.is_dir():
        logger.error(f"Results directory not found: {results_base_path}")
        raise HTTPException(status_code=404, detail=f"Results directory not found: {results_base_path}")
    
    try:
        # Parse the result ID to extract components
        # Expected format: timestamp_workload_branch_experiment_number
        id_parts = result_id.split('_')
        if len(id_parts) < 4:
            raise HTTPException(status_code=400, detail="Invalid result ID format")
        
        # Join the remaining parts back (in case workload or branch names contain underscores)
        remaining_parts = id_parts[:-1]
        
        # Find the result by searching through the directory structure
        for results_dir in results_base_path.iterdir():
            if not results_dir.is_dir():
                continue
                
            timestamp = results_dir.name.strip()
            
            for workload_dir in results_dir.iterdir():
                if not workload_dir.is_dir():
                    continue
                    
                workload_name = workload_dir.name.strip()
                
                for branch_dir in workload_dir.iterdir():
                    if not branch_dir.is_dir():
                        continue
                        
                    branch_name = branch_dir.name.strip()
                    
                    # Check if this combination matches our ID
                    expected_id = f"{timestamp}_{workload_name}_{branch_name}"
                    if expected_id == result_id:
                        # Verify the experiment directory exists
                        exp_dir = branch_dir
                        if not exp_dir.is_dir():
                            continue
                            
                        # Count iterations
                        iterations_count = sum(1 for item in exp_dir.iterdir() if item.is_dir())
                        
                        return ResultEntry(
                            id=result_id,
                            workload=workload_name,
                            branch_name=branch_name,
                            timestamp=timestamp,
                            iterations=iterations_count
                        )
        
        # If we get here, the result wasn't found
        raise HTTPException(status_code=404, detail=f"Result with ID '{result_id}' not found")
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except PermissionError:
        logger.exception("Permission error while accessing results directory.")
        raise HTTPException(status_code=500, detail="Permission denied when accessing results.")
    except Exception as e:
        logger.exception(f"Unexpected error while retrieving result '{result_id}'.")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while retrieving result: {str(e)}")

@app.get("/api/results/{result_id}/download")
def download_results(result_id: str):
    """Download a specific result as a zip file."""
    results_base_path = Path(RESULTS_DIR)
    
    # Check for results directory
    if not results_base_path.exists():
        raise HTTPException(status_code=404, detail=f"Results directory {results_base_path} does not exist. Did you run any experiments?")
    
    try:
        # Parse the result ID to extract components
        # Expected format: timestamp_workload_branch_experiment_number
        id_parts = result_id.split('_')
        if len(id_parts) < 4:
            raise HTTPException(status_code=400, detail="Invalid result ID format")
        
        # The last part should be the experiment number
        try:
            experiment_number = int(id_parts[-1])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid experiment number in result ID")
        
        # Extract timestamp from result_id 
        # Format: timestamp_workload_branch_experiment, where timestamp includes date and time
        # We need to find where the timestamp part ends and workload begins
        # Timestamp format appears to be: YYYY-MM-DD_HH-MM-SS
        
        # Split the ID and reconstruct the timestamp (first two parts joined by _)
        id_parts = result_id.split('_')
        if len(id_parts) < 4:
            raise HTTPException(status_code=400, detail="Invalid result ID format")
        
        # Timestamp should be the first two parts: date_time
        timestamp = f"{id_parts[0]}_{id_parts[1]}"
        timestamp_folder = results_base_path / timestamp
        
        # Check if timestamp folder exists
        if not timestamp_folder.is_dir():
            raise HTTPException(status_code=404, detail=f"Timestamp folder '{timestamp}' not found")
        
        # Create zip file with the entire timestamp folder
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Include the entire timestamp folder and all its contents
            for file_path in timestamp_folder.rglob("*"):
                if file_path.is_file():
                    # Preserve the full directory structure starting from timestamp folder
                    # This creates: timestamp/workload/branch/experiment/files
                    relative_path = file_path.relative_to(timestamp_folder.parent)
                    zip_file.write(file_path, relative_path)
        
        # Prepare the buffer for reading
        zip_buffer.seek(0)
        
        # Create a descriptive filename using the timestamp
        safe_filename = f"{timestamp}.zip"
        
        # Return the zip file as a streaming response
        return StreamingResponse(
            io.BytesIO(zip_buffer.read()),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={safe_filename}"}
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except PermissionError:
        logger.exception("Permission error while accessing results directory.")
        raise HTTPException(status_code=500, detail="Permission denied when accessing results.")
    except Exception as e:
        logger.exception(f"Unexpected error while downloading result '{result_id}'.")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while downloading result: {str(e)}")
    
@app.get("/api/config/sut/{sut_name}", response_model=SUTConfig)
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

@app.post("/api/deploy/sut", status_code=status.HTTP_202_ACCEPTED)
def deploy_sut(request: DeployRequest):
    """Deploy a specific SUT in a separate process, ensuring only one deployment runs at a time."""
    with state_lock:
        if is_deploying.value == 1:
            raise HTTPException(
                status_code=409,
                detail="A deployment is already running."
            )
        is_deploying.value = 1

    sut_name = request.sut_name
    deploy_only = request.deploy_only
    experiment_name = request.experiment_name
    n_iterations = request.n_iterations
    sut_filename = f"{sut_name}.yaml"
    sut_path = os.path.join(SUT_CONFIGS_DIR, sut_filename)
    
    if not os.path.isfile(sut_path):
        with state_lock:
            is_deploying.value = 0
        raise HTTPException(status_code=404, detail=f"SUT configuration not found: {request.sut_name}")
    
    config = Config(sut_config=sut_path, clue_config=CLUE_CONFIG_PATH)
    
    try:
        process = multiprocessing.Process(
            target=run_deployment,
            args=(config, experiment_name, sut_name, deploy_only, n_iterations, state_lock, is_deploying)
        )
        process.start()
    except Exception as e:
        with state_lock:
            is_deploying.value = 0
        logger.error(f"Failed to start deployment process: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start deployment: {str(e)}")
    
    return {"message": f"Deployment of SUT {sut_name} has been started."}

@app.get("/plot/list")
def list_plots(request: ResultEntry, iteration: int):
    """List all available plots for a specific iteration."""
    workload = request.workload
    branch_name = request.branch_name
    experiment_number = iteration
    timestamp = request.timestamp

    results_path = Path(RESULTS_DIR) / timestamp / workload / branch_name / str(experiment_number)
    
    if not results_path.exists():
        raise HTTPException(status_code=404, detail=f"No results found for the specified iteration: {results_path}")

    supported_formats = ["*.png", "*.jpg", "*.jpeg", "*.svg"]
    plots = []
    for file_format in supported_formats:
        plots.extend([file.name for file in results_path.glob(file_format)])
    return {"plots": plots}

@app.get("/plot/download")
def download_plot(request: ResultEntry):
    """Download a specific plot for a given iteration."""
    workload = request.workload
    branch_name = request.branch_name
    experiment_number = request.experiment_number
    timestamp = request.timestamp
    plot_filename = request.plot_filename
    results_path = Path(RESULTS_DIR) / timestamp / workload / branch_name / str(experiment_number)
    plot_path = results_path / plot_filename
    if not plot_path.exists():
        raise HTTPException(status_code=404, detail=f"Plot file not found: {plot_path}")
    return StreamingResponse(
        open(plot_path, "rb"),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={plot_filename}"}
    )