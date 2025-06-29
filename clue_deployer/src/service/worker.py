import multiprocessing as mp
from clue_deployer.src.service.experiment_queue import ExperimentQueue
from clue_deployer.src.logger import get_child_process_logger, logger, shared_log_buffer
from clue_deployer.src.models.deploy_request import DeployRequest
from clue_deployer.src.main import ExperimentRunner
from clue_deployer.src.configs.configs import ENV_CONFIG, Configs
from fastapi import HTTPException

SUT_CONFIGS_DIR = ENV_CONFIG.SUT_CONFIGS_PATH
CLUE_CONFIG_PATH = ENV_CONFIG.CLUE_CONFIG_PATH


class WorkerManager(mp.BaseManager):
    pass

WorkerManager.register('ExperimentQueue', ExperimentQueue)
WorkerManager.register('DeployRequest', DeployRequest)

class Worker:
    def __init__(self):
        self.shared_flag = mp.Value('b', True)
        self.state_lock = mp.Lock()
        self.is_deploying = mp.Value('i', 0)
        
        
        self.process_logger = get_child_process_logger(f"NO_SUT", shared_log_buffer)
        
        self.condition = mp.Condition()
        
        self.manager = WorkerManager()
        self.manager.start()
        
        self.current_deploy_request = WorkerManager.DeployRequest
        self.experiment_queue = WorkerManager.ExperimentQueue(condition=self.condition)

        self.process = mp.Process(
            target=self._worker_loop,
            args=(
                self.shared_flag,
                self.state_lock,
                self.is_deploying,
                self.condition,
                self.experiment_queue,
                shared_log_buffer
            )
        )
        
        


    def _worker_loop(self, shared_flag, 
                     state_lock, 
                     is_deploying, 
                     condition, 
                     experiment_queue, 
                     log_buffer):
        with self.state_lock:
            if is_deploying.value == 1:
                raise HTTPException(
                    status_code=409,
                    detail="A deployment is already running."
                )
            is_deploying.value = 1
        self.process_logger.info("Worker process started and ready to deploy experiments.")
        while shared_flag.value:
            with condition:
                # Wait until the queue is not empty or shared_flag is False
                while experiment_queue.is_empty() and shared_flag.value:
                    self.condition.wait()

                # Exit if shared_flag is no longer True
                if not shared_flag.value:
                    break

                # Dequeue the experiment
                experiment: DeployRequest = self.experiment_queue.dequeue()

                self.process_logger = get_child_process_logger(
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
                
                configs = Configs(sut_config=sut_path, clue_config=CLUE_CONFIG_PATH)
            
                self.process_logger.info(f"Starting deployment for SUT {experiment.sut}")
                runner = ExperimentRunner(
                    configs,
                    variants=experiment.variants,
                    sut=experiment.sut,
                    deploy_only=experiment.deploy_only,
                    n_iterations=experiment.n_iterations,
                )
                runner.main()
                self.process_logger.info(f"Successfully completed deployment for SUT {experiment.sut}")
            except Exception as e:
                self.process_logger.error(f"Deployment process failed for SUT {experiment.sut}: {str(e)}")
        
        # Clean up the deployment state
        with state_lock:
            is_deploying.value = 0
        self.process_logger.info(f"Deployment process for SUT {experiment.sut} finished")
    
    def start(self):
        if self.process.is_alive():
            raise RuntimeError("Worker process is already running.")
        
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
        self.process.terminate()
        self.process.join()
        logger.info("Worker killed.")

