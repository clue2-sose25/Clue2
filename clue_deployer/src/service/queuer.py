import json
import multiprocessing as mp
from contextlib import contextmanager
from clue_deployer.src.service.experiment_queue import ExperimentQueue
from clue_deployer.src.logger import get_child_process_logger, logger, shared_log_buffer, process_logger
from clue_deployer.src.models.deploy_request import DeployRequest
from clue_deployer.src.models.experiment import Experiment
from clue_deployer.src.main import ExperimentRunner
from clue_deployer.src.configs.configs import ENV_CONFIG, Configs
from fastapi import HTTPException
from kubernetes.client import CoreV1Api
from kubernetes.client.exceptions import ApiException   
from clue_deployer.src.service.status_manager import StatusManager, StatusPhase
from clue_deployer.src.service.final_status import FinalStatus

SUT_CONFIGS_DIR = ENV_CONFIG.SUT_CONFIGS_PATH
CLUE_CONFIG_PATH = ENV_CONFIG.CLUE_CONFIG_PATH

class Queuer:
    def __init__(self):
        self.shared_flag = mp.Value('b', True)
        self.state_lock = mp.Lock()
        self.is_deploying = mp.Value('i', 0)
        
        # Use multiprocessing.Manager for shared data structures
        self.manager = mp.Manager()
        self.shared_container = self.manager.dict()
        self.experiment_queue = ExperimentQueue(condition=mp.Condition())
        self.condition = self.manager.Condition()
        self.shared_container['current_experiment'] = None

        self.process_logger = get_child_process_logger(
            "NO_SUT",
            shared_log_buffer
        )
        self.process = None
        self.core_v1_api = CoreV1Api()
    
    @property
    def current_experiment(self) -> DeployRequest | None:
        """
        Get the current deployment request from the shared container.
        """
        experiment : Experiment | None = self.shared_container.get('current_experiment')
        if experiment is None:
            return None
        
        # Convert Experiment to DeployRequest
        return DeployRequest(
            variants=[v.name for v in experiment.variants],
            workloads=[w.name for w in experiment.workloads],
            sut=experiment.sut,
            n_iterations=experiment.n_iterations,
            deploy_only=experiment.deploy_only
        )

    @current_experiment.setter
    def current_experiment(self, experiment: Experiment):
        """
        Set the current deployment in the shared container.
        """
        self.shared_container['current_experiment'] = experiment

    def _new_process(self):
        self.process = mp.Process(
            target=self._worker_loop,
            args=(
                self.shared_flag,
                self.state_lock,
                self.is_deploying,
                self.condition,
                self.experiment_queue,
                self.shared_container,
            )
        )

    def _worker_loop(self, 
                     shared_flag, 
                     state_lock, 
                     is_deploying, 
                     condition, 
                     experiment_queue, 
                     shared_container):
        
        # Create worker-specific logger
        worker_logger = get_child_process_logger("WORKER", shared_log_buffer)
        
        # Set deployment state at the start
        with state_lock:
            if is_deploying.value == 1:
                raise HTTPException(
                    status_code=409,
                    detail="A deployment is already running."
                )
            is_deploying.value = 1
        
        worker_logger.info("Worker process started and ready to deploy experiments.")
        condition = mp.Condition()
        
        try:
            while shared_flag.value:
                with condition:
                    # Wait until the queue is not empty or shared_flag is False
                    while experiment_queue.is_empty() and shared_flag.value:
                        condition.wait()

                    # Exit if shared_flag is no longer True
                    if not shared_flag.value:
                        break

                    # Check if queue is still empty after waiting (could be spurious wakeup)
                    if experiment_queue.is_empty():
                        continue

                    # Dequeue the experiment
                    experiment: DeployRequest = experiment_queue.dequeue()
                    
                    # FIX: Use consistent key name
                    shared_container['current_experiment'] = experiment

                try:
                    sut_filename = f"{experiment.sut}.yaml"
                    sut_path = SUT_CONFIGS_DIR.joinpath(sut_filename)
                    
                    if not sut_path.exists():
                        worker_logger.error(f"SUT configuration file {sut_filename} does not exist.")
                        # Clear current experiment and continue
                        shared_container['current_experiment'] = None
                        continue
                    
                    configs = Configs(sut_config_path=sut_path, clue_config_path=CLUE_CONFIG_PATH)
                
                    worker_logger.info(f"Starting deployment for SUT {experiment.sut}")
                    runner = ExperimentRunner(
                        configs,
                        variants=experiment.variants,
                        workloads=experiment.workloads,
                        sut=experiment.sut,
                        deploy_only=experiment.deploy_only,
                        n_iterations=experiment.n_iterations,
                    )
                    
                    # FIX: Update shared container with the actual experiment object
                    shared_container['current_experiment'] = runner.experiment
                    
                    # FIX: Access experiment from shared container
                    current_exp = shared_container['current_experiment']
                    current_exp.make_experiemnts_dir()
                    
                    with self.experiment_manager_worker(experiment.sut, worker_logger, shared_container):
                        runner.main()
                    
                    worker_logger.info(f"Successfully completed deployment for SUT {experiment.sut}")
                    
                except Exception as e:
                    worker_logger.error(f"Deployment process failed for SUT {experiment.sut}: {str(e)}")
                    
                    # Perform cleanup for failed experiment
                    try:
                        current_exp = shared_container.get('current_experiment')
                        if current_exp:
                            self._worker_cleanup(current_exp, FinalStatus.ERROR, worker_logger)
                    except Exception as cleanup_error:
                        worker_logger.error(f"Failed to cleanup after deployment error: {cleanup_error}")
                    
                    # Clear current experiment before continuing
                    shared_container['current_experiment'] = None
                
                # After processing an experiment, check if queue is empty
                if experiment_queue.is_empty():
                    worker_logger.info("Queue is empty, worker process will exit.")
                    break
                    
        except Exception as e:
            worker_logger.error(f"Critical error in worker loop: {str(e)}")
            
        finally:
            # Always clean up the deployment state when worker loop exits
            with state_lock:
                is_deploying.value = 0
            
            # Clear current experiment
            shared_container['current_experiment'] = None
            worker_logger.info("Worker loop finished, deployment state reset")
    
    def start(self):
        # Clean up any dead processes first
        if self.process and not self.process.is_alive():
            self.process = None
        
        if self.process and self.process.is_alive():
            raise RuntimeError("Worker process is already running.")
        
        # Reset deployment state if no active process
        if not self.is_process_alive():
            with self.state_lock:
                self.is_deploying.value = 0
        
        if self.is_deploying.value == 1:
            raise RuntimeError("Worker is already deploying an experiment.")
        
        if self.experiment_queue.is_empty():
            raise RuntimeError("Experiment queue is empty. Cannot start worker.")
            
        self.shared_flag.value = True
        self._new_process()  # Create a new process instance
        self.process.start()
        logger.info("Worker process started successfully.")
    
    def stop(self):
        logger.info("Stopping worker queue and waiting for current deployment to finish...")
        self.shared_flag.value = False
        if self.process and self.process.is_alive():
            self.process.join()
        logger.info("Worker stopped.")

    def kill(self):
        with self.state_lock:
            if self.is_deploying.value == 0:
                raise ValueError("Worker is not currently deploying. Cannot kill the process.")
            self.is_deploying.value = 0
        
        StatusManager.set(StatusPhase.NO_DEPLOYMENT, "Worker process killed by user.")
        self.shared_flag.value = False
        logger.info("Stopping worker queue by killing the process...")
        if self.process and self.process.is_alive():
            self.process.kill()
            self.process.join()
        logger.info("Worker killed.")
        self._cleanup(FinalStatus.ERROR)

    def is_process_alive(self) -> bool:
        """Check if the worker process is still alive."""
        return self.process is not None and self.process.is_alive()

    def cleanup_dead_process(self):
        """Clean up references to dead worker processes."""
        if self.process and not self.process.is_alive():
            logger.info("Cleaning up dead worker process reference.")
            self.process = None
            with self.state_lock:
                self.is_deploying.value = 0
            self.shared_container['current_experiment'] = None

    def check_and_reset_stale_deployment(self):
        """
        Check if the worker process died unexpectedly and reset deployment state.
        This should be called by the parent process periodically or before operations.
        """
        if self.is_deploying.value == 1 and not self.is_process_alive():
            logger.warning("Worker process died unexpectedly. Resetting deployment state.")
            with self.state_lock:
                self.is_deploying.value = 0
            
            # Clear current experiment
            self.shared_container['current_experiment'] = None
            StatusManager.set(StatusPhase.NO_DEPLOYMENT, "Worker process died unexpectedly.")
            self._cleanup_if_experiment_exists(FinalStatus.ERROR)

    def _cleanup_if_experiment_exists(self, status):
        """Only cleanup if there's actually an experiment to cleanup."""
        current_exp = self.shared_container.get('current_experiment')
        if current_exp:
            self._cleanup(status)

    @contextmanager
    def experiment_manager(self, sut_name):
        """Context manager to ensure cleanup after worker operations (main process)."""
        original_logger = getattr(process_logger, 'logger', None)
        process_logger.logger = sut_name
        try:
            yield
        finally:
            self.is_deploying.value = 0
            process_logger.logger = original_logger or "MAIN"
            process_logger.info(f"Cleaning up after deployment for SUT {sut_name}")
            self._cleanup(FinalStatus.SUCCESS)

    @contextmanager
    def experiment_manager_worker(self, sut_name, worker_logger, shared_container):
        """Context manager for worker process operations."""
        original_logger = getattr(worker_logger, 'logger', None)
        worker_logger.logger = sut_name
        try:
            yield
        finally:
            # Don't modify is_deploying here - it will be handled in main loop
            worker_logger.logger = original_logger or "WORKER"
            worker_logger.info(f"Cleaning up after deployment for SUT {sut_name}")
    
    def _worker_cleanup(self, experiment, status, worker_logger):
        """Clean up worker resources for a failed experiment."""
        worker_logger.info("Cleaning up worker resources after failure...")
        
        if not experiment:
            worker_logger.warning("No experiment to clean up.")
            return
            
        try:
            exp_dir = experiment.get_experiment_dir()
            StatusManager.set(StatusPhase.NO_DEPLOYMENT, f"Deployment failed: {status}")

            # Write status file
            with open(exp_dir.joinpath("status.json"), 'w') as f:
                json.dump({"status": status}, f)
                
            worker_logger.info(f"Cleanup completed for failed experiment")
            
        except Exception as e:
            worker_logger.error(f"Error during worker cleanup: {e}")

    def _cleanup(self, status):
        """Clean up the worker resources."""
        logger.info("Cleaning up worker resources...")
        
        # FIX: Get current experiment from shared container
        current_exp = self.shared_container.get('current_experiment')
        if not current_exp:
            logger.warning("No current experiment to clean up.")
            return
            
        # namespace = current_exp.configs.sut_config.namespace
        exp_dir = current_exp.get_experiment_dir()

        StatusManager.set(StatusPhase.NO_DEPLOYMENT, "Worker process finished deployment.")

        try:
            with open(exp_dir.joinpath("status.json"), 'w') as f:
                json.dump({"status": status}, f)
        
        except FileNotFoundError as e:
            logger.error(f"could not locate experiment dir: {exp_dir}")
            raise e

        # Clean up the namespace if it exists
        # try:
        #     self.core_v1_api.read_namespace(name=namespace)
        #     logger.info(f"Namespace '{namespace}' exists. Deleting it...")
        #     self.core_v1_api.delete_namespace(name=namespace)
        # except ApiException as e:
        #     logger.error(f"Failed to read namespace '{namespace}': {e}")
        
        # Clear the current experiment
        self.shared_container['current_experiment'] = None