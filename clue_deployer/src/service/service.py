import os
from contextlib import asynccontextmanager
from threading import Lock
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
import multiprocessing
from clue_deployer.src.models.deploy_request import DeployRequest
from clue_deployer.src.models.health_response import HealthResponse
from clue_deployer.src.models.status_response import StatusResponse
from clue_deployer.src.service.status_manager import StatusManager
from clue_deployer.src.logger import SharedLogBuffer, get_child_process_logger, logger, shared_log_buffer
from clue_deployer.src.configs.configs import ENV_CONFIG, Configs
from clue_deployer.src.main import ExperimentRunner
from clue_deployer.src.service.worker import Worker
from .routers import logs, suts, results, plots, cluster, results_server, clue_config
from clue_deployer.src.service.grafana_manager import GrafanaManager


# Initialize multiprocessing lock and value for deployment synchronization. Used for deployments.

worker = Worker()
state_lock = worker.state_lock
is_deploying = worker.is_deploying

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
# Add routers
app.include_router(logs.router)
app.include_router(suts.router)
app.include_router(results.router)
app.include_router(plots.router)
app.include_router(cluster.router)
app.include_router(results_server.router)
app.include_router(clue_config.router)



SUT_CONFIGS_DIR = ENV_CONFIG.SUT_CONFIGS_PATH
RESULTS_DIR = ENV_CONFIG.RESULTS_PATH
CLUE_CONFIG_PATH = ENV_CONFIG.CLUE_CONFIG_PATH

def run_experiment(configs: Configs, deploy_request: DeployRequest,
                  state_lock: Lock, is_deploying, shared_log_buffer: SharedLogBuffer):
    """Function to run the deployment in a separate process."""
    # Setup logger for this child process
    process_logger = get_child_process_logger(f"DEPLOY_{deploy_request.sut}", shared_log_buffer)
    
    try:
        process_logger.info(f"Starting deployment for SUT {deploy_request.sut}")
        runner = ExperimentRunner(configs, deploy_request.variants, deploy_request.workloads, 
                           deploy_request.deploy_only, deploy_request.sut, deploy_request.n_iterations)
        runner.main()
        process_logger.info(f"Successfully completed deployment for SUT {deploy_request.sut}")
        
    except Exception as e:
        process_logger.error(f"Deployment process failed for SUT {deploy_request.sut}: {str(e)}")
    finally:
        with state_lock:
            is_deploying.value = 0
        process_logger.info(f"Deployment process for SUT {deploy_request.sut} finished")

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

@app.post("/api/deploy/sut", status_code=status.HTTP_202_ACCEPTED)
async def deploy_sut(request: DeployRequest):
    """Deploy a specific SUT in a separate process, ensuring only one deployment runs at a time."""
    with state_lock:
        if is_deploying.value == 1:
            raise HTTPException(
                status_code=409,
                detail="A deployment is already running."
            )
        is_deploying.value = 1

    sut_filename = f"{request.sut}.yaml"
    sut_path = os.path.join(SUT_CONFIGS_DIR, sut_filename)
    
    if not os.path.isfile(sut_path):
        with state_lock:
            is_deploying.value = 0
        raise HTTPException(status_code=404, detail=f"SUT configuration not found: {request.sut}")
    
    configs = Configs(sut_path, CLUE_CONFIG_PATH)
    
    try:
        # Pass the shared buffer to the child process
        process = multiprocessing.Process(
            target=run_experiment,
            args=(configs, request, 
                  state_lock, is_deploying, shared_log_buffer)
        )
        process.start()
        logger.info(f"Started deployment process for SUT {request.sut}")
    except Exception as e:
        with state_lock:
            is_deploying.value = 0
        logger.error(f"Failed to start deployment process: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start deployment: {str(e)}")
    
    return {"message": f"Deployment of SUT {request.sut} has been started."}

@app.post("/api/queue/enqueue", status_code=status.HTTP_202_ACCEPTED)
def enqueue_experiment(request: list[DeployRequest]):
    """
    Enqueue a list of deployment requests to the experiment queue.
    """ 
    if not request:
        raise HTTPException(status_code=400, detail="Request body cannot be empty")
    if len(request) == 0:
        raise HTTPException(status_code=400, detail="No requests provided")
    
    for deploy_request in request:
        worker.experiment_queue.enqueue(deploy_request)
    
    logger.info(f"Enqueued {len(request)} deployment requests.")
    return {"message": f"Enqueued {len(request)} deployment requests."}


@app.post("/api/deploy/start", status_code=status.HTTP_202_ACCEPTED)
def deploy_from_queue():
    """
    start deploy worker
    """
    try:
        worker.start()
    except Exception as e:
        logger.error(f"Failed to start deployment worker: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                             detail=f"Failed to start deployment worker: {str(e)}")
    
    logger.info("Deployment worker started.")
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"message": "Deployment worker started."})
    
    

@app.delete("api/deploy/kill", status_code=status.HTTP_204_NO_CONTENT)
def deploy_kill():
    """
    Kill the current deployment process.
    """
    
    
    # Terminate the worker process
    try:
        worker.terminate()
    except Exception as e:
        logger.error(f"Failed to terminate deployment process: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                             detail=f"Failed to terminate deployment: {str(e)}")

    logger.info("Deployment process terminated.")
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

@app.delete("api/deploy/stop", status_code=status.HTTP_204_NO_CONTENT)
def stop_deployment():
    """
    Stop the current deployment process gracefully.
    """
    try:
        worker.stop()
    except Exception as e:
        logger.error(f"Failed to stop deployment process: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                             detail=f"Failed to stop deployment: {str(e)}")

    logger.info("Deployment process stopped.")
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

@app.delete("/api/queue/flush", status_code=status.HTTP_204_NO_CONTENT)
def flush_queue():
    """Flush the deployment queue."""
    worker.experiment_queue.flush()
    logger.info("Experiment queue flushed.")
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

@app.get("/api/queue/status")
def get_queue_status():
    """Get the current status of the deployment queue."""
    queue_size = worker.experiment_queue.size()
    return {
        "queue_size": queue_size,
        "queue": worker.experiment_queue.get_all()
    }


