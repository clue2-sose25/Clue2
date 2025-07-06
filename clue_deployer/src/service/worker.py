import multiprocessing as mp
from multiprocessing.managers import BaseManager
from clue_deployer.src.service.experiment_queue import ExperimentQueue
from clue_deployer.src.logger import get_child_process_logger, logger, shared_log_buffer
from clue_deployer.src.models.deploy_request import DeployRequest
from clue_deployer.src.models.experiment import Experiment
from clue_deployer.src.main import ExperimentRunner
from clue_deployer.src.configs.configs import ENV_CONFIG, Configs
from fastapi import HTTPException
from kubernetes.client import CoreV1Api
from kubernetes.client.exceptions import ApiException   

SUT_CONFIGS_DIR = ENV_CONFIG.SUT_CONFIGS_PATH
CLUE_CONFIG_PATH = ENV_CONFIG.CLUE_CONFIG_PATH
class Worker:
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
    def current_experiment(self):
        """
        Get the current deployment from the shared container.
        """
        return self.shared_container.get('current_experiment', None)

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
                get_child_process_logger("NO_SUT", shared_log_buffer),
                self.shared_container,
            )
        )

    def _worker_loop(self, 
                     shared_flag, 
                     state_lock, 
                     is_deploying, 
                     condition, 
                     experiment_queue, 
                     process_logger,
                     shared_container):
        
        with self.state_lock:
            if is_deploying.value == 1:
                raise HTTPException(
                    status_code=409,
                    detail="A deployment is already running."
                )
            is_deploying.value = 1
        
        process_logger.info("Worker process started and ready to deploy experiments.")
        condition = mp.Condition()
        while shared_flag.value:
            with condition:
                # Wait until the queue is not empty or shared_flag is False
                while experiment_queue.is_empty() and shared_flag.value:
                    condition.wait()

                # Exit if shared_flag is no longer True
                if not shared_flag.value:
                    break

                # Dequeue the experiment
                experiment: DeployRequest = self.experiment_queue.dequeue()

                shared_container['current_deployment'] = experiment



                process_logger = get_child_process_logger(
                    experiment.sut,
                    shared_log_buffer
                )

            try:
                sut_filename = f"{experiment.sut}.yaml"
                sut_path = SUT_CONFIGS_DIR.joinpath(sut_filename)
                
                if not sut_path.exists():
                    with state_lock:
                        is_deploying.value = 0
                    self.process_logger.error(f"SUT configuration file {sut_filename} does not exist.")
                    continue
                
                configs = Configs(sut_config_path=sut_path, clue_config_path=CLUE_CONFIG_PATH)
            
                process_logger.info(f"Starting deployment for SUT {experiment.sut}")
                runner = ExperimentRunner(
                    configs,
                    variants=experiment.variants,
                    sut=experiment.sut,
                    deploy_only=experiment.deploy_only,
                    n_iterations=experiment.n_iterations,
                )
                self.current_experiment = runner.experiment

                runner.main()
                process_logger.info(f"Successfully completed deployment for SUT {experiment.sut}")
            except Exception as e:
                process_logger.error(f"Deployment process failed for SUT {experiment.sut}: {str(e)}")
        
        # Clean up the deployment state
        with state_lock:
            is_deploying.value = 0
        process_logger.info(f"Deployment process for SUT {experiment.sut} finished")
    
    def start(self):
        if self.process and self.process.is_alive():
            raise RuntimeError("Worker process is already running.")
        
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
        self.process.join()
        logger.info("Worker stopped.")

    def kill(self):
        with self.state_lock:
            if self.is_deploying.value == 0:
                raise ValueError("Worker is not currently deploying. Cannot kill the process.")
            self.is_deploying.value = 0
        
        self.shared_flag.value = False
        logger.info("Stopping worker queue by killing the process...")
        self.process.kill()
        self.process.join()
        logger.info("Worker killed.")
        #self.is_deploying.value = 0
        self._cleanup()

    
    def _cleanup(self):
        """Clean up the worker resources."""
        #TODO write the deployment status to the status file
        logger.info("Cleaning up worker resources...")
        if not self.current_experiment:
            logger.warning("No current experiment to clean up.")
            return
        namespace = self.current_experiment.configs.sut_config.namespace
        
        # Clean up the namespace if it exists
        try:
            self.core_v1_api.read_namespace(name=namespace)
            logger.info(f"Namespace '{namespace}' exits. Deleting it...")
            self.core_v1_api.delete_namespace(name=namespace)
        except ApiException as e:
            logger.error(f"Failed to read namespace '{namespace}': {e}")
        

    
    

