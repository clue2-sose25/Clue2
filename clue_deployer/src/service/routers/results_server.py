import threading
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from fastapi import APIRouter, HTTPException
from clue_deployer.src.configs.configs import ENV_CONFIG
from clue_deployer.src.logger import logger
from clue_deployer.src.results.data_analysis import DataAnalysis
from clue_deployer.src.service.routers.results import find_experiment_by_uuid, find_experiment_directory_by_uuid

SUT_CONFIGS_DIR = ENV_CONFIG.SUT_CONFIGS_PATH
RESULTS_DIR = ENV_CONFIG.RESULTS_PATH

router = APIRouter()

@dataclass
class ServerInfo:
    """Information about a running server."""
    uuid: str
    sut_name: str
    server_instance: Any
    thread: threading.Thread



class ServerManager:
    """Manages server instances and their lifecycle."""
    
    def __init__(self):
        self._current_server: Optional[ServerInfo] = None
        self._lock = threading.Lock()
    
    def stop_current_server(self) -> None:
        """Stop the currently running server if any."""
        with self._lock:
            if self._current_server is None:
                return
            
            server_info = self._current_server
            
            try:
                # Stop the server
                if hasattr(server_info.server_instance, 'stop_server'):
                    server_info.server_instance.stop_server()
                elif hasattr(server_info.server_instance, 'shutdown'):
                    server_info.server_instance.shutdown()
                else:
                    logger.warning("Current server doesn't have a stop method")
                
                logger.info(f"Stopped previous server for UUID: {server_info.uuid}")
                
            except Exception as e:
                logger.exception("Error stopping current server")
            
            # Wait for thread to finish (with timeout)
            if server_info.thread.is_alive():
                server_info.thread.join(timeout=5.0)
                if server_info.thread.is_alive():
                    logger.warning("Previous server thread did not terminate gracefully")
            
            # Clean up
            self._current_server = None
    
    def _start_server_thread(self, uuid: str, sut_name: str, experiment_dir: Path) -> None:
        """Function to run the server in a separate thread."""
        logger.info("Starting a server in a new thread")
        try:
            # Start the data server
            da = DataAnalysis(experiment_dir, f"/app/sut_configs/{sut_name}.yaml", load_data_from_file=True)
            da.create_server()
            
            # Store the server instance (thread-safe update)
            with self._lock:
                if self._current_server is not None:
                    # Update the server instance in the existing ServerInfo
                    self._current_server.server_instance = da
                
            logger.info(f"Results server started for UUID: {uuid}, SUT: {sut_name}")
            
        except Exception as e:
            logger.exception(f"Error starting server for UUID {uuid}: {e}")
            # Clean up on error
            with self._lock:
                self._current_server = None
    
    def start_server(self, uuid: str, sut_name: str, experiment_dir: Path) -> Dict[str, Any]:
        """Start a new server, stopping any existing one first."""
        with self._lock:
            # Stop any existing server first
            if self._current_server is not None:
                logger.info(f"Stopping existing server for UUID: {self._current_server.uuid}")
                # Release lock temporarily for stopping
                self._current_server_to_stop = self._current_server
                self._current_server = None
        
        # Stop outside of lock to avoid deadlock
        if hasattr(self, '_current_server_to_stop') and self._current_server_to_stop is not None:
            self._stop_server_instance(self._current_server_to_stop)
            delattr(self, '_current_server_to_stop')
        
        with self._lock:
            # Create and start the new server thread
            server_thread = threading.Thread(
                target=self._start_server_thread,
                args=(uuid, sut_name, experiment_dir),
                daemon=True,
                name=f"ResultsServer-{uuid}"
            )
            
            # Create ServerInfo with placeholder server_instance (will be set by thread)
            self._current_server = ServerInfo(
                uuid=uuid,
                sut_name=sut_name,
                server_instance=None,  # Will be set by the thread
                thread=server_thread
            )
            
            server_thread.start()
            
            return {
                "message": f"Successfully started results server for UUID: {uuid}, SUT: {sut_name}",
                "uuid": uuid,
                "sut_name": sut_name,
                "status": "starting"
            }
    
    def _stop_server_instance(self, server_info: ServerInfo) -> None:
        """Stop a specific server instance."""
        try:
            # Stop the server
            if server_info.server_instance and hasattr(server_info.server_instance, 'stop_server'):
                server_info.server_instance.stop_server()
            elif server_info.server_instance and hasattr(server_info.server_instance, 'shutdown'):
                server_info.server_instance.shutdown()
            else:
                logger.warning("Server doesn't have a stop method")
            
            logger.info(f"Stopped server for UUID: {server_info.uuid}")
            
        except Exception as e:
            logger.exception("Error stopping server")
        
        # Wait for thread to finish (with timeout)
        if server_info.thread.is_alive():
            server_info.thread.join(timeout=5.0)
            if server_info.thread.is_alive():
                logger.warning("Server thread did not terminate gracefully")
    
    def get_current_server_info(self) -> Optional[Dict[str, str]]:
        """Get information about the current running server."""
        with self._lock:
            if self._current_server is None:
                return None
            return {
                "uuid": self._current_server.uuid,
                "sut_name": self._current_server.sut_name
            }

# Create a global server manager instance
server_manager = ServerManager()

@router.post("/api/results/{uuid}/startResultsServer")
async def start_results_server(uuid: str):
    """Starts a results server by UUID from URL path. Fetches SUT from experiment data. Stops any existing server first."""
    logger.info(f"Start Server: {uuid}")
    
    results_base_path = Path(RESULTS_DIR)
    
    # Check for results directory
    if not results_base_path.is_dir():
        logger.error(f"Results directory not found: {results_base_path}")
        raise HTTPException(status_code=404, detail=f"Results directory not found: {results_base_path}")
    
    try:
        # Find the experiment data by UUID
        experiment_data = find_experiment_by_uuid(uuid, results_base_path)
        
        if experiment_data is None:
            raise HTTPException(status_code=404, detail=f"Experiment with UUID {uuid} not found")
        
        # Extract SUT name from experiment data
        sut_name = experiment_data.get("sut")
        if not sut_name:
            raise HTTPException(status_code=400, detail=f"SUT name not found in experiment data for UUID {uuid}")
        
        # Find the experiment directory by UUID
        experiment_dir = find_experiment_directory_by_uuid(uuid, results_base_path)
        
        if experiment_dir is None:
            raise HTTPException(status_code=404, detail=f"Experiment directory with UUID {uuid} not found")
        
        # Use the server manager to start the server
        result = server_manager.start_server(uuid, sut_name, experiment_dir)
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Unexpected error while starting server for experiment {uuid}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while starting server: {str(e)}")