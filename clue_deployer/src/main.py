import json
import os
import time
from typing import List
import uuid
import urllib3
from pathlib import Path
from datetime import datetime
from os import path
from kubernetes import config as kube_config
from clue_deployer.src.configs.configs import CONFIGS, Configs
from clue_deployer.src.models.experiment import Experiment
from clue_deployer.src.models.status_phase import StatusPhase
from clue_deployer.src.service.status_manager import StatusManager
from clue_deployer.src.models.variant import Variant
from clue_deployer.src.variant_runner import VariantRunner
from clue_deployer.src.models.workload import Workload
from clue_deployer.src.variant_deployer import VariantDeployer
from clue_deployer.src.logger import process_logger as logger

# Disable SSL verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ExperimentRunner:
    def __init__(self,
                configs: Configs = CONFIGS,
                variants: list[str] = CONFIGS.env_config.VARIANTS,
                workloads: list[str] = CONFIGS.env_config.WORKLOADS,
                deploy_only = CONFIGS.env_config.DEPLOY_ONLY,
                sut: str = CONFIGS.env_config.SUT,
                n_iterations: int = CONFIGS.env_config.N_ITERATIONS,
                uuid = uuid.uuid4()) -> None:
        # Load the kube config
        try:
            if os.getenv("KUBERNETES_SERVICE_HOST"):
                kube_config.load_incluster_config()
            else:
                kube_config.load_kube_config()
        except Exception as exc:
            if os.getenv("DEPLOY_AS_SERVICE", "false").lower() == "true":
                logger.warning(f"Failed to load kubeconfig: {exc}")
            else:
                raise
        # Load the correct SUT config
        CONFIGS.replace_sut_config(sut)
        # Prepare the variants
        logger.info(f"Specified variants: {variants}")
        final_variants: List[Variant] = [variant for variant in CONFIGS.sut_config.variants if variant.name in variants]
        # Check if variants are valid and set colected to true if inside the same cluster
        if os.getenv("KUBERNETES_SERVICE_HOST"):
            for v in final_variants:
                v.colocated_workload = True
        # Prepare the workloads
        logger.info(f"Specified workloads: {workloads}")
        final_workloads: List[Workload] = [workload for workload in CONFIGS.sut_config.workloads if workload.name in workloads]
        # Create the final experiment object
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.experiment = Experiment(
            id = uuid,
            configs = configs,
            sut = sut,
            variants = final_variants,
            workloads = final_workloads,
            n_iterations = n_iterations,
            timestamp = self.timestamp,
            deploy_only= deploy_only
        )

    @staticmethod
    def available_suts():
        """
        Reads the 'sut_configs' folder and returns a list of available SUT names.
        """
        if not CONFIGS.env_config.SUT_CONFIGS_PATH.exists():
            logger.error(f"SUT configs folder not found: {CONFIGS.env_config.SUT_CONFIGS_PATH}")
            raise FileNotFoundError(f"SUT configs folder not found: {CONFIGS.env_config.SUT_CONFIGS_PATH}")
        sut_files = [f.stem for f in CONFIGS.env_config.SUT_CONFIGS_PATH.glob("*.yaml")]
        return sut_files


    def create_experiment_files(self, results_path: str, results_parent_path: str) -> None:
        """
        Create experiment configuration and status files in the specified results path.
        
        Args:
            results_path: The whole directory path where all data files will be stored. Only creating the directories here.
            results_parent_path: The directory path where the parent files should be created: experiment.json and status.json
        """
        # Create all directories if they don't exist
        logger.info(f"Creating the results folder: {results_path}")
        os.makedirs(results_path, exist_ok=False)
        # Create the full file path for experiment.json
        logger.info("Creating the experiment.json in the results folder")
        experiment_file_path = path.join(results_parent_path, 'experiment.json')
        # Copy the experiment object into json
        with open(experiment_file_path, 'w') as f:
            f.write(self.experiment.to_json())
        # Create status file
        logger.info("Creating the status.json in the results folder")
        status_file_path = path.join(results_parent_path, 'status.json')
        status_data = {"status": "STARTED"}
        with open(status_file_path, 'w') as f:
            json.dump(status_data, f, indent=2)

    def execute_single_run(self, variant: Variant, workload: Workload | None, results_path: Path | None) -> None:
        """
        Executes and runs a single variant
        """
        logger.info(f"Deploying the SUT: {self.experiment.sut}")
        # Deploy the SUT
        variant_deployer = VariantDeployer(variant)
        variant_deployer.deploy_SUT(results_path)
        # If not deploy only, run the workload
        if not self.experiment.deploy_only:
            # Wait for the SUT before stressing the SUT with a workload
            logger.info(f"Waiting {CONFIGS.sut_config.wait_before_workloads}s before starting workload")
            time.sleep(CONFIGS.sut_config.wait_before_workloads)  
            logger.info("Starting the workload")
            # Run the variant
            variant_runner = VariantRunner(variant, workload)
            variant_runner.run(results_path)
            # Clean up the system
            logger.info("Cleaning up after the experiment")
            variant_runner.cleanup(variant_deployer.helm_wrapper)


    def iterate_single_variant(self, variant: Variant) -> None:
        """
        Iterates over a single variant of the experiment
        """
        num_iterations = self.experiment.n_iterations
        logger.info(f"Starting variant: {variant}")
        # Run all iterations for the variant
        for workload in self.experiment.workloads:
            logger.info(f"Starting workload: {variant}/{workload.name}")
            # Iterate over workload types
            for iteration in range(num_iterations):
                # Create the results path for the individual runs
                results_path = path.join("data", self.experiment.sut, self.experiment.timestamp, workload.name, variant.name, str(iteration))
                # Create the results path for the experiment parent folder (inside the timestamp directory)
                results_parent_path = path.join("data", self.experiment.sut, self.experiment.timestamp)
                # Create experiment files
                self.create_experiment_files(results_path, results_parent_path)
                # Iterate
                logger.info(f"Starting iteration ({iteration + 1}/{num_iterations}) for {variant.name}/{workload.name})")
                self.execute_single_run(variant, workload, results_path)
                # additional wait after each iteration except the last one
                if iteration < num_iterations - 1:
                    logger.info(f"Sleeping {CONFIGS.sut_config.wait_after_workloads} seconds before next iteration")
                    time.sleep(CONFIGS.sut_config.wait_after_workloads)

    def main(self) -> None:
        logger.info(f"Starting CLUE with DEPLOY_ONLY={self.experiment.deploy_only}")
        logger.info("Disabled SLL verification for urllib3")
        # Check if SUT is valid
        available_suts_list = self.available_suts()
        if self.experiment.sut not in available_suts_list:
            logger.error(f"Invalid SUT name: '{self.experiment.sut}'")
            logger.info(f"Available SUTs: {available_suts_list}")
            return
        # Set the status to preparing
        StatusManager.set(StatusPhase.PREPARING_CLUSTER, "Preparing the cluster...")
        # Deploy a single variant if deploy only
        if self.experiment.deploy_only:
            #logger.info(f"Starting deployment only for variant: {self.experiment.variants[0]} (workload: {self.experiment.workloads[0]})")
            #self.execute_single_run(self.experiment.variants[0], self.experiment.workloads[0])
            logger.info(f"Starting deployment only for variant: {self.experiment.variants[0]} (workload: None)")
            self.execute_single_run(self.experiment.variants[0], None, None)
            logger.info("Deploy only experiment executed successfully.")
        else:
            # Run over all variants of the experiment
            for variant in self.experiment.variants:
                self.iterate_single_variant(variant)
                # Additional wait after each variant except the last one
                if variant != self.experiment.variants[-1]:
                    logger.info(f"Sleeping additional {CONFIGS.sut_config.wait_after_workloads} seconds before starting next variant")
                    time.sleep(CONFIGS.sut_config.wait_after_workloads)
            logger.info("All variants executed successfully. Finished running the experiment.")


if __name__ == "__main__":
    ExperimentRunner().main()