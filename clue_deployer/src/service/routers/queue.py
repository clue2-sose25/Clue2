from fastapi import APIRouter
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from clue_deployer.src.models.deploy_request import DeployRequest
from clue_deployer.src.logger import logger
from clue_deployer.src.service.worker import Worker

router = APIRouter()

worker = Worker()
state_lock = worker.state_lock
is_deploying = worker.is_deploying


@router.post("/api/queue/enqueue", status_code=status.HTTP_202_ACCEPTED)
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

@router.get("/api/queue/current", status_code=status.HTTP_200_OK)
async def get_current_deployment():
    logger.info("Fetching current deployment status.")
    current_deployment = worker.current_experiment
    return current_deployment

@router.post("/api/queue/deploy", status_code=status.HTTP_202_ACCEPTED)
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
    
    

@router.delete("/api/queue/kill", status_code=status.HTTP_204_NO_CONTENT)
def deploy_kill():
    """
    Kill the current deployment process.
    """
    
    
    # Terminate the worker process
    try:
        worker.kill()
    except Exception as e:
        logger.error(f"Failed to terminate deployment process: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                             detail=f"Failed to terminate deployment: {str(e)}")

    logger.info("Deployment process killed.")
    return 

@router.delete("/api/queue/stop", status_code=status.HTTP_204_NO_CONTENT)
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

@router.delete("/api/queue/flush", status_code=status.HTTP_204_NO_CONTENT)
def flush_queue():
    """Flush the deployment queue."""
    worker.experiment_queue.flush()
    logger.info("Experiment queue flushed.")
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

@router.get("/api/queue/status")
def get_queue_status():
    """Get the current status of the deployment queue."""
    queue_size = worker.experiment_queue.size()
    return {
        "queue_size": queue_size,
        "queue": worker.experiment_queue.get_all()
    }