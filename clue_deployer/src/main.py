import os
import time
import uuid
from clue_deployer.src.models.result_entry import ResultEntry
import urllib3
import progressbar
from pathlib import Path
from datetime import datetime
from os import path
import progressbar
from kubernetes import config as kube_config
from clue_deployer.src.config.config import CONFIGS, ENV_CONFIG, Config
from clue_deployer.src.models.status_phase import StatusPhase
from clue_deployer.src.service.status_manager import StatusManager
from clue_deployer.src.models.experiment import Experiment
from clue_deployer.src.experiment_runner import ExperimentRunner
from clue_deployer.src.experiment_workloads import get_workload_instance
from clue_deployer.src.experiment_list import ExperimentList
from clue_deployer.src.deploy import ExperimentDeployer
from clue_deployer.src.logger import logger

# Disable SSL verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load K8s config
kube_config.load_kube_config()


class ClueRunner:
    def __init__(self, 
                config: Config = CONFIGS, 
                variants: str = ENV_CONFIG.VARIANTS,
                workloads: str = ENV_CONFIG.WORKLOADS,
                deploy_only = ENV_CONFIG.DEPLOY_ONLY,
                sut: str = ENV_CONFIG.SUT,
                n_iterations: int = CONFIGS.clue_config.n_iterations) -> None:
        self.config: Config = config
        self.variants: list[str] = variants.split(",")
        self.workloads: list[str] = workloads.split(",")
        self.deploy_only: bool = deploy_only
        self.sut: str = sut
        self.n_iterations: int = n_iterations
        # Create the results entry
        self.result_entry = ResultEntry(
            id = uuid.uuid4(),
            sut = self.sut,
            variants = self.variants,
            workloads = self.workloads,
            n_iterations = self.n_iterations,
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        )

    @staticmethod
    def available_suts():
        """
        Reads the 'sut_configs' folder and returns a list of available SUT names.
        """
        if not ENV_CONFIG.SUT_CONFIGS_PATH.exists():
            logger.error(f"SUT configs folder not found: {ENV_CONFIG.SUT_CONFIGS_PATH}")
            raise FileNotFoundError(f"SUT configs folder not found: {ENV_CONFIG.SUT_CONFIGS_PATH}")
        # Get all YAML files in the 'sut_configs' folder
        sut_files = [f.stem for f in ENV_CONFIG.SUT_CONFIGS_PATH.glob("*.yaml")]
        return sut_files


    def run_single_experiment(self, exp: Experiment, observations_out_path: Path|None = None) -> None:
        """
        Executes and runs a single experiment
        """
        # Create the experiment folder if necessary
        if observations_out_path is not None:
            logger.info("Creating a results folder")
            try:
                os.makedirs(observations_out_path, exist_ok=False)
            except OSError:
                logger.warning("Data for this experiment already exist, skipping")
                raise RuntimeError("Data for this experiment already exist, skipping")
        else:
            logger.info("Skipping creating a results directory")
        logger.info("Deploying the SUT")
        # Deploy the SUT
        experiment_deployer = ExperimentDeployer(exp, self.config)
        experiment_deployer.deploy_SUT()
        # If not deploy only, run the benchmark
        if not self.deploy_only:
            logger.info("Starting the benchmark")
            # Wait for the SUT
            logger.info(f"Waiting {exp.env.wait_before_workloads}s before starting workload")
            time.sleep(exp.env.wait_before_workloads)  # wait for 120s before stressing the workload
            # Run the experiment
            ExperimentRunner(exp).run(observations_out_path)
            # Clean up
            logger.info("Cleaning up after the experiment")
            ExperimentRunner(exp).cleanup(experiment_deployer.helm_wrapper)


    def iterate_single_experiment(self, exp: Experiment) -> None:
        """
        Iterates over the experiment
        """
        num_iterations = self.n_iterations
        logger.info(f"Starting {exp} experiment")
        # Run all iterations
        for i in range(num_iterations):
            # Create the results path
            results_path = path.join("data", self.result_entry.sut, self.result_entry.timestamp, exp.name, "workload_name" ,str(i))
            logger.info(f"Running iteration ({i + 1}/{num_iterations}) with output to: {results_path}")
            self.run_single_experiment(exp, results_path)
            # additional wait after each iteration except the last one
            if i < num_iterations - 1:
                logger.info(f"Sleeping {exp.env.wait_after_workloads} seconds before next experiment iteration")
                time.sleep(exp.env.wait_after_workloads)

    def main(self) -> None:
        logger.info(f"Starting CLUE with DEPLOY_ONLY={self.deploy_only}")
        logger.info("Disabled SLL verification for urllib3")
        # Check if SUT is valid
        available_suts_list = self.available_suts()
        if self.sut not in available_suts_list:
            logger.error(f"Invalid SUT name: '{self.sut}'")
            logger.info(f"Available SUTs: {available_suts_list}")
            return
        # Load the experiments
        exps = ExperimentList.load_experiments(CONFIGS, self.variants)
        logger.info(f"Loaded {len(exps.experiments)} experiments to run")
        # Check if the list is not empty
        if not len(exps.experiments):
            raise ValueError(f"Invalid experiment name for {self.sut}")
        # Set the status to preparing
        StatusManager.set(StatusPhase.PREPARING_CLUSTER, "Preparing the cluster...")
        # Deploy a single experiment if deploy only
        if self.deploy_only:
            logger.info(f"Starting deployment only for experiment: {exps.experiments[0]}")
            self.run_single_experiment(exps.experiments[0])
            logger.info("Deployment executed successfully. Exiting CLUE.")
        else:
            # Get the workloads
            logger.info("Appending workloads to the experiments")
            workloads = [get_workload_instance(w) for w in self.config.clue_config.workloads]
            exps.add_workloads(workloads)
            # Sort and log the experiments
            exps.sort()
            logger.info("Running the following experiments:")
            i = 0
            for exp in exps.experiments:
                logger.info(f"Experiment no.{i}: {exp}")
                i = i + 1
            progressbar.streams.wrap_stderr()
            # Run over all iterations of each of the experiments
            for exp in exps:
                self.iterate_single_experiment(exp)
                # additional wait after each experiment except the last one
                if exp != exps.experiments[-1]:
                    logger.info(f"Sleeping additional {exp.env.wait_after_workloads} seconds before starting next experiment")
                    time.sleep(exp.env.wait_after_workloads)
                                
            logger.info("All experiments executed successfully. Exiting CLUE.")


if __name__ == "__main__":
    ClueRunner().main()