import os
import time
import uuid
from clue_deployer.src.models.experiment import Experiment
import urllib3
from pathlib import Path
from datetime import datetime
from os import path
from kubernetes import config as kube_config
from clue_deployer.src.config.config import CONFIGS, ENV_CONFIG, Config
from clue_deployer.src.models.status_phase import StatusPhase
from clue_deployer.src.service.status_manager import StatusManager
from clue_deployer.src.models.variant import Variant
from clue_deployer.src.models.variant_environment import VariantEnvironment
from clue_deployer.src.variant_runner import VariantRunner
from clue_deployer.src.models.workloads import Workload, get_workload_instance
from clue_deployer.src.experiment_deployer import ExperimentDeployer
from clue_deployer.src.logger import logger

# Disable SSL verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load K8s config
kube_config.load_kube_config()


class ExperimentRunner:
    def __init__(self, 
                configs: Config = CONFIGS, 
                variants: str = ENV_CONFIG.VARIANTS,
                workloads: str = ENV_CONFIG.WORKLOADS,
                deploy_only = ENV_CONFIG.DEPLOY_ONLY,
                sut: str = ENV_CONFIG.SUT,
                n_iterations: int = ENV_CONFIG.N_ITERATIONS) -> None:
        # Prepare the variants object
        variants_config = configs.variants_config
        final_variants: list[Variant] = []
        for variant in variants_config.variants:
            # Create an Experiment instance for each experiment in the YAML file
            if variant.name in variants:
                # Add variant to the list
                final_variants.append(Variant(
                    name=variant.name,
                    target_branch=variant.target_branch,
                    colocated_workload=variant.colocated_workload,  # TODO default False
                    env=VariantEnvironment(configs),
                    autoscaling=variant.autoscaling,
                    critical_services=variant.critical_services,
                    config=configs,
                ))
        # Prepare the workloads
        splitWorkloads = workloads.split(",")
        workloads: list[Workload] = [get_workload_instance(workload) for workload in splitWorkloads]
        # Create the final experiment object
        self.experiment = Experiment(
            id = uuid.uuid4(),
            configs = configs,
            sut = sut,
            variants = final_variants,
            workloads = workloads,
            n_iterations = n_iterations,
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
            deploy_only= deploy_only
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


    def execute_single_run(self, variant: Variant, results_path: Path) -> None:
        """
        Executes and runs a single variant
        """
        # Create the results folder if necessary
        logger.info(f"Creating the results folder: {results_path}")
        try:
            os.makedirs(results_path, exist_ok=False)
        except OSError:
            logger.error("Error creating a results folder!")
            raise RuntimeError("Error creating a results folder")
        logger.info(f"Deploying the SUT: {self.experiment.sut}")
        # Deploy the SUT
        experiment_deployer = ExperimentDeployer(variant, self.experiment.configs)
        experiment_deployer.deploy_SUT(results_path)
        # If not deploy only, run the benchmark
        if not self.experiment.deploy_only:
            logger.info("Starting the benchmark")
            # Wait for the SUT before stressing the SUT with a workload
            logger.info(f"Waiting {variant.env.wait_before_workloads}s before starting workload")
            time.sleep(variant.env.wait_before_workloads)  
            # Run the experiment
            VariantRunner(variant).run(results_path)
            # Clean up
            logger.info("Cleaning up after the experiment")
            VariantRunner(variant).cleanup(experiment_deployer.helm_wrapper)


    def iterate_single_variant(self, variant: Variant) -> None:
        """
        Iterates over a single variant of the experiment
        """
        num_iterations = self.experiment.n_iterations
        logger.info(f"Starting {variant} variant")
        # Run all iterations for the variant
        for iteration in range(num_iterations):
            # Create the results path
            results_path = path.join("data", self.experiment.sut, self.experiment.timestamp, variant.name, "workload_name" , str(iteration))
            logger.info(f"Running iteration ({iteration + 1}/{num_iterations})")
            self.execute_single_run(variant, results_path)
            # additional wait after each iteration except the last one
            if iteration < num_iterations - 1:
                logger.info(f"Sleeping {variant.env.wait_after_workloads} seconds before next experiment iteration")
                time.sleep(variant.env.wait_after_workloads)

    def main(self) -> None:
        logger.info(f"Starting CLUE with DEPLOY_ONLY={self.experiment.deploy_only}")
        logger.info("Disabled SLL verification for urllib3")
        # Check if SUT is valid
        # TODO: More checks for the workloads, variants, etc.
        available_suts_list = self.available_suts()
        if self.experiment.sut not in available_suts_list:
            logger.error(f"Invalid SUT name: '{self.experiment.sut}'")
            logger.info(f"Available SUTs: {available_suts_list}")
            return
        logger.info(f"Selected {len(self.experiment.variants)} variants to run")
        logger.info(f"Selected {len(self.experiment.workloads)} workloads to run")
        # Set the status to preparing
        StatusManager.set(StatusPhase.PREPARING_CLUSTER, "Preparing the cluster...")
        # Deploy a single variant if deploy only
        if self.experiment.deploy_only:
            logger.info(f"Starting deployment only for variant: {self.experiment.variants[0]}")
            self.execute_single_run(self.experiment.variants[0])
            logger.info("Deploy only experiment executed successfully.")
        else:
            # Run over all variants of the experiment
            for variant in self.experiment.variants:
                self.iterate_single_variant(variant)
                # Additional wait after each variant except the last one
                if variant != self.experiment.variants[-1]:
                    logger.info(f"Sleeping additional {variant.env.wait_after_workloads} seconds before starting next variant")
                    time.sleep(variant.env.wait_after_workloads)
            logger.info("All variants executed successfully. Finished running the experiment.")


if __name__ == "__main__":
    ExperimentRunner().main()