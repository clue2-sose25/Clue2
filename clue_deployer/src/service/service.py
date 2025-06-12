import json
import os
import zipfile
import io
import shutil
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse, RedirectResponse
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
from clue_deployer.src.logger import get_child_process_logger, logger, shared_log_buffer
from clue_deployer.src.config.config import ENV_CONFIG
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

def run_deployment(config, experiment_name, sut_name, deploy_only, n_iterations, 
                  state_lock, is_deploying, shared_log_buffer):
    """Function to run the deployment in a separate process."""
    # Setup logger for this child process
    process_logger = get_child_process_logger(f"DEPLOY_{sut_name}", shared_log_buffer)
    
    try:
        process_logger.info(f"Starting deployment for SUT {sut_name}")
        runner = ClueRunner(config, experiment_name=experiment_name, sut_name=sut_name, 
                           deploy_only=deploy_only, n_iterations=n_iterations)
        
        # You might want to pass the process_logger to ClueRunner if it accepts a logger parameter
        # runner = ClueRunner(config, experiment_name=experiment_name, sut_name=sut_name, 
        #                    deploy_only=deploy_only, n_iterations=n_iterations, logger=process_logger)
        
        runner.main()
        process_logger.info(f"Successfully completed deployment for SUT {sut_name}")
        
    except Exception as e:
        process_logger.error(f"Deployment process failed for SUT {sut_name}: {str(e)}")
    finally:
        with state_lock:
            is_deploying.value = 0
        process_logger.info(f"Deployment process for SUT {sut_name} finished")

@app.get("/api/status", response_model=StatusResponse)
def read_status():
    """Endpoint to check if a deployment is currently in progress."""
    with state_lock:
        deploying = bool(is_deploying.value)
    return StatusResponse(is_deploying=deploying, phase=None, message=None)
    # TO-DO: Add multi-threaded status 
    phase, msg = StatusManager.get()
    return StatusResponse(phase=phase, message=msg or None)

@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(message="true")

@app.get("/api/logs")
def get_logs(n: int = None):
    """Get recent logs from the shared buffer."""
    try:
        logs = shared_log_buffer.get_logs(n)
        return {"logs": logs, "count": len(logs)}
    except Exception as e:
        logger.error(f"Failed to retrieve logs: {str(e)}")
        return {"logs": [], "count": 0, "error": str(e)}

@app.delete("/api/logs")
def clear_logs():
    """Clear the log buffer."""
    try:
        shared_log_buffer.clear()
        logger.info("Log buffer cleared")
        return {"message": "Log buffer cleared successfully"}
    except Exception as e:
        logger.error(f"Failed to clear logs: {str(e)}")
        return {"error": str(e)}


@app.get("/api/logs/stream")
async def stream_logs():
    """Stream log buffer updates using Server-Sent Events."""

    async def event_generator():
        last_count = 0
        last_version = shared_log_buffer.get_version()  # Track version to detect clears

        # Send initial logs
        try:
            current_logs = shared_log_buffer.get_logs()
            if current_logs:
                for log in current_logs:
                    yield f"data: {json.dumps({'log': log})}\n\n"
                last_count = len(current_logs)
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Failed to get initial logs: {str(e)}'})}\n\n"

        # Stream new logs
        while True:
            try:
                await asyncio.sleep(0.5)

                current_version = shared_log_buffer.get_version()
                current_logs = shared_log_buffer.get_logs()
                current_count = len(current_logs)

                # If buffer was cleared, reset counters
                if current_version != last_version:
                    last_version = current_version
                    last_count = 0

                # Send new logs
                if current_count > last_count:
                    new_logs = current_logs[last_count:]
                    for log in new_logs:
                        yield f"data: {json.dumps({'log': log})}\n\n"
                    last_count = current_count

            except Exception as e:
                yield f"data: {json.dumps({'error': f'Stream error: {str(e)}'})}\n\n"
                await asyncio.sleep(1)  # Slow down on error

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@app.get("/api/suts", response_model=SutsResponse)
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
        timestamp = f"{id_parts[0]}_{id_parts[1]}"
        timestamp_folder = results_base_path / timestamp
        
        logger.info(timestamp_folder)
        
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

@app.delete("/api/results/{result_id}")
def delete_result(result_id: str):
    """Delete a specific result directory."""
    results_base_path = Path(RESULTS_DIR)

    if not results_base_path.exists():
        raise HTTPException(status_code=404, detail=f"Results directory {results_base_path} does not exist")

    try:
        # Locate the directory matching the provided ID by traversing
        for timestamp_dir in results_base_path.iterdir():
            if not timestamp_dir.is_dir():
                continue
            timestamp = timestamp_dir.name.strip()

            for workload_dir in timestamp_dir.iterdir():
                if not workload_dir.is_dir():
                    continue
                workload_name = workload_dir.name.strip()

                for branch_dir in workload_dir.iterdir():
                    if not branch_dir.is_dir():
                        continue
                    branch_name = branch_dir.name.strip()

                    expected_id = f"{timestamp}_{workload_name}_{branch_name}"
                    if expected_id == result_id:
                        # Remove the branch directory and clean up parents
                        shutil.rmtree(branch_dir)

                        if not any(workload_dir.iterdir()):
                            workload_dir.rmdir()
                            if not any(timestamp_dir.iterdir()):
                                timestamp_dir.rmdir()

                        return {"message": f"Result {result_id} deleted"}

        # If we reach here, the result wasn't found
        raise HTTPException(status_code=404, detail=f"Result with ID '{result_id}' not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error while deleting result '{result_id}'.")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while deleting result: {str(e)}")
        
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
        # Pass the shared buffer to the child process
        process = multiprocessing.Process(
            target=run_deployment,
            args=(config, experiment_name, sut_name, deploy_only, n_iterations, 
                  state_lock, is_deploying, shared_log_buffer)
        )
        process.start()
        logger.info(f"Started deployment process for SUT {sut_name}")
    except Exception as e:
        with state_lock:
            is_deploying.value = 0
        logger.error(f"Failed to start deployment process: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start deployment: {str(e)}")
    
    return {"message": f"Deployment of SUT {sut_name} has been started."}

@app.get("/api/plots")
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

@app.get("/api/plots/download")
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