import os
import logging
import zipfile
import io
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, RedirectResponse
from pathlib import Path
import yaml
from clue_deployer.src.config.config import ENV_CONFIG
from clue_deployer.src.main import ClueRunner
from clue_deployer.src.config import SUTConfig, Config
from clue_deployer.service.status_manager import StatusManager
from clue_deployer.service.models import (
    HealthResponse,
    Sut,
    SutListResponse,
    Timestamp,
    Iteration,
    ResultTimestampResponse,
    DeployRequest,
    StatusOut,
    SingleIteration
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic: Add redirect from / to /docs
    from starlette.routing import Route
    async def redirect_to_docs(request):
        return RedirectResponse(url="/docs")
    app.router.routes.insert(0, Route("/", endpoint=redirect_to_docs, methods=["GET"]))
    yield  # Yield control to the application
    # Shutdown logic (if any) would go here

app = FastAPI(title="CLUE Deployer Service", lifespan=lifespan)

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

@app.get("/api/status", response_model=StatusOut)
def read_status():
    phase, msg = StatusManager.get()
    return StatusOut(phase=phase, message=msg or None)

@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(message="true")

@app.get("/api/list/sut", response_model=SutListResponse)
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

        return SutListResponse(suts=suts)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing SUTs: {str(e)}")

@app.get("/api/list/results", response_model=ResultTimestampResponse)
async def list_all_results():
    """List all results, structured by timestamp, workload, branch, and experiment number."""
    results_base_path = Path(RESULTS_DIR)

    if not results_base_path.is_dir():
        logger.error(f"Results directory not found: {results_base_path}")
        raise HTTPException(status_code=404, detail=f"Results directory not found: {results_base_path}")
    
    try:
        processed_timestamps = []
        
        for timestamp_dir in results_base_path.iterdir():
            if not timestamp_dir.is_dir():
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
                            raise ValueError(f"experiment_number {exp_num_str} cannot be casted into an integer.")
            
            processed_timestamps.append(timestamp_data_obj)
            
        return ResultTimestampResponse(results=processed_timestamps)
    except PermissionError:
        logger.exception("Permission error while accessing results directory.")
        raise HTTPException(status_code=500, detail="Permission denied when accessing results.")
    except Exception as e:
        logger.exception("Unexpected error while retrieving results.")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while retrieving results: {str(e)}")

@app.get("/api/download/results")
def download_results():
    """Download all results as a zip file."""
    results_path = Path(RESULTS_DIR)
    if not results_path.exists():
        raise HTTPException(status_code=404, detail=f"Results directory {results_path} does not exist.\
                             Did you run any experiments?")
    
    # Create an in-memory zip file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in results_path.rglob("*"):
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

@app.post("/api/deploy/sut")
def deploy_sut(request: DeployRequest):
    """Deploy a specific SUT."""
    sut_name = request.sut_name
    deploy_only = request.deploy_only
    experiment_name = request.experiment_name
    n_iterations = request.n_iterations
    sut_filename = f"{sut_name}.yaml"
    sut_path = os.path.join(SUT_CONFIGS_DIR, sut_filename)
    
    if not os.path.isfile(sut_path):
        raise HTTPException(status_code=404, detail=f"SUT configuration not found: {request.sut_name}")
    
    config = Config(sut_config=sut_path, clue_config=CLUE_CONFIG_PATH)
    try:
        # run the clue main method
        runner = ClueRunner(config, experiment_name=experiment_name, sut_name=sut_name, deploy_only=deploy_only, n_iterations=n_iterations)
        runner.main()
        return {"message": f"SUT {request.sut_name} has been deployed successfully."}
    except Exception as e:
        logger.error(f"Failed to deploy SUT {request.sut_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to deploy SUT: {str(e)}")

@app.get("/plot/list")
def list_plots(request: SingleIteration):
    """List all available plots for a specific iteration."""
    workload = request.workload
    branch_name = request.branch_name
    experiment_number = request.experiment_number
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
def download_plot(request: SingleIteration):
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