import os
import asyncio
import json
from contextlib import asynccontextmanager
from threading import Lock
from typing import Any
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import RedirectResponse, StreamingResponse
import multiprocessing
from clue_deployer.src.models.deploy_request import DeployRequest
from clue_deployer.src.models.health_response import HealthResponse
from clue_deployer.src.models.status_response import StatusResponse
from clue_deployer.src.service.status_manager import StatusManager
from clue_deployer.src.logger import get_child_process_logger, logger, shared_log_buffer, SharedLogBuffer
from clue_deployer.src.main import ExperimentRunner
from clue_deployer.src.configs.configs import Configs, ENV_CONFIG
from .routers.queue import worker
from .routers import logs, suts, results, plots, cluster, results_server, clue_config, queue


# Initialize multiprocessing lock and value for deployment synchronization. Used for deployments.
state_lock = Lock()
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
app.include_router(queue.router)
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
        phase, message = StatusManager.get()
    return StatusResponse(is_deploying=deploying, phase=phase, message=message)

@app.get("/api/status/stream")
async def stream_status(request: Request):
    """Stream status updates using Server-Sent Events."""

    async def event_generator():
        with state_lock:
            last_deploying = bool(is_deploying.value)
        last_phase, last_detail = StatusManager.get()

        # Send initial status
        initial = {
            "is_deploying": last_deploying,
            "phase": last_phase.value,
            "detail": last_detail,
        }
        yield f"data: {json.dumps(initial)}\n\n"

        while True:
            if await request.is_disconnected():
                break
            await asyncio.sleep(0.5)

            with state_lock:
                deploying = bool(is_deploying.value)
            phase, detail = StatusManager.get()

            if deploying != last_deploying or phase != last_phase or detail != last_detail:
                last_deploying = deploying
                last_phase = phase
                last_detail = detail
                update = {
                    "is_deploying": deploying,
                    "phase": phase.value,
                    "detail": detail,
                }
                yield f"data: {json.dumps(update)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )

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




