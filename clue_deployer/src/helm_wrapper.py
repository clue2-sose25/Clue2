
import subprocess
from pathlib import Path
import tempfile
import shutil
from clue_deployer.src.models.variant import Variant
from clue_deployer.src.logger import logger
from clue_deployer.src.config import Config
from clue_deployer.src.config.helm_dependencies import Dependencies

class HelmWrapper():
    
    def __init__(self, config: Config, experiment: Variant):
        self.clue_config = config.clue_config
        self.experiment = experiment
        self.sut_config = config.sut_config
        self.values_file_full_path = self.sut_config.helm_chart_path / self.sut_config.values_yaml_name
        self.name = self.sut_config.sut_path.name
        # Path to the ORIGINAL Helm chart in the SUT directory
        self.original_helm_chart_path = Path(self.sut_config.helm_chart_path) # Ensure this is a Path
        self.original_values_file_name = self.sut_config.values_yaml_name
        # This will be set when a temporary chart copy is active
        self.active_chart_path: Path | None = None
        self.active_values_file_path: Path | None = None
        self._temp_dir_context = None # To manage the TemporaryDirectory context
    

    def _create_temp_chart_copy(self) -> Path:
        """
        Copies the original Helm chart to a new temporary directory.
        Returns the path to the root of the copied chart in the temporary directory.
        """
        if not self.original_helm_chart_path.is_dir():
            raise FileNotFoundError(f"Original Helm chart directory not found at {self.original_helm_chart_path}")

        
        # This creates a temporary directory that will be cleaned up automatically
        self._temp_dir_context = tempfile.TemporaryDirectory()
        temp_dir_path = Path(self._temp_dir_context.name)

        # The copied chart will be inside this temp_dir, maintaining its original name
        copied_chart_root_path = temp_dir_path / self.original_helm_chart_path.name
        
        shutil.copytree(self.original_helm_chart_path, copied_chart_root_path)
        
        self.active_chart_path = copied_chart_root_path
        self.active_values_file_path = copied_chart_root_path / self.original_values_file_name
        
        if not self.active_values_file_path.exists():
            raise FileNotFoundError(f"Values file not found in copied chart at {self.active_values_file_path}")
        return copied_chart_root_path
    

    def __enter__(self):
        """
        Support using HelmWrapper as a context manager for temp dir handling.
        """
        logger.info("Creating temp directory for helm chart")
        self._create_temp_chart_copy()
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Ensures the temp folder cleanup when exiting context.
        """
        logger.info("Cleaning up temp directory")
        if self._temp_dir_context:
            self._temp_dir_context.cleanup()
            self._temp_dir_context = None
        self.active_chart_path = None
        self.active_values_file_path = None

    def update_helm_chart(self) -> dict:
        """
        Updates the values.yaml file with replacements specified in the SUT config
        """
        logger.info(f"Using values file from path: {self.active_values_file_path}")
        if not self.active_values_file_path.exists():
            raise FileNotFoundError(f"Values file not found at {self.active_values_file_path}")
        # Open the values file
        with open(self.active_values_file_path, "r") as f:
            values = f.read()
        # Apply all replacements
        helm_replacements = self.sut_config.helm_replacements
        logger.info(f"Applying {len(helm_replacements)} helm replacements from the SUT config")
        # Loop through replacements
        for replacement in helm_replacements:
            # If the new value contains the placeholder, replace it with the experiment tag
            if replacement.new_value.__contains__("__EXPERIMENT_TAG__"):
                new_tag = self.experiment.target_branch
                replacement.new_value = replacement.new_value.replace("__EXPERIMENT_TAG__", new_tag)
                values = values.replace(replacement.old_value, replacement.new_value)
            elif replacement.should_apply(autoscaling=self.experiment.autoscaling):
                no_instances = values.count(replacement.old_value)
                if no_instances > 0:
                    logger.info(f"Replacing {no_instances} instances of: {replacement}")
                    values = values.replace(replacement.old_value, replacement.new_value)
                else:
                    logger.warning(f"No instances found for replacement: {replacement}")
            else:
                logger.info(f"Skipping replacement due to unmet conditions: {replacement}")

        # Save the changes
        with open(self.active_values_file_path, "w") as f:
            f.write(values)
        logger.info(f"Wrote patched values.yml: {self.active_values_file_path}")
        return values
    

    def _add_helm_repos(self) -> None:
        """
        Adds Helm repositories
        """
        if self.sut_config.helm_dependencies_from_chart:
            logger.info("Helm dependencies from chart")
            chart_path = self.sut_config.helm_chart_path.joinpath("Chart.yaml")
            if not chart_path.exists():
                raise FileNotFoundError(f"Chart.yaml not found at {chart_path}. Cannot add dependencies from chart.")
            
            
            dependencies = Dependencies.load_from_yaml(chart_path)
            for dependency in dependencies.dependencies:
                logger.info(f"Adding Helm repository {dependency.name} at {dependency.repository}")
                helm_repo_add = subprocess.run(
                    ["helm", "repo", "add", dependency.name, dependency.repository],
                    capture_output=True,
                    text=True
                )
                if helm_repo_add.returncode != 0:
                    logger.error(f"Failed to add Helm repository {dependency.name}. Exit code: {helm_repo_add.returncode}")
                    logger.error(f"STDOUT: {helm_repo_add.stdout}")
                    logger.error(f"STDERR: {helm_repo_add.stderr}")
                    raise RuntimeError(f"Failed to add Helm repository {dependency.name}. Check the logs for details.")
                logger.info(helm_repo_add.stdout)
        else:
            #TODO maybe allow adding repositories from the SUT config?
            pass
    
    def _build_dependencies(self) -> None:
        """
        Builds Helm chart dependencies.
        """
        try:
            self._add_helm_repos()
            logger.info(f"Building Helm dependencies for chart at {self.active_chart_path}")
            helm_dependency_build = subprocess.run(
                ["helm", "dependency", "build", self.active_chart_path],
                capture_output=True,
                text=True
            )
            if helm_dependency_build.returncode != 0:
                logger.error(f"Failed to build Helm dependencies. Exit code: {helm_dependency_build.returncode}")
                logger.error(f"STDOUT: {helm_dependency_build.stdout}")
                logger.error(f"STDERR: {helm_dependency_build.stderr}")
                raise RuntimeError("Failed to build Helm dependencies. Check the logs for details.")
            logger.info(f"Helm dependency build output:\n{helm_dependency_build.stdout}")
        except subprocess.CalledProcessError as cpe:
            logger.error(f"Error building Helm dependencies: {cpe}")
            raise cpe

    def deploy_sut(self) -> None:
        """
        Deploys the SUT's helm chart
        """
        if self.active_chart_path is None:
            raise RuntimeError("Temporary chart path not set. Did you call _create_temp_chart_copy()?")
        #building helm dependencies
        self._build_dependencies()
        try:
            
            logger.info(f"Deploying helm chart for {self.name} in namespace {self.sut_config.namespace}")
            helm_deploy = subprocess.run(
                ["helm", "upgrade", "--install", self.name, "-n", self.sut_config.namespace, "."],
                cwd=self.active_chart_path,
                capture_output=True,  # Capture both stdout and stderr
                text=True  # Decode output to string automatically
            )
            if helm_deploy.returncode != 0:
                logger.error(f"Helm command failed with exit code {helm_deploy.returncode}")
                logger.error(f"STDOUT: {helm_deploy.stdout}")
                logger.error(f"STDERR: {helm_deploy.stderr}")
                raise RuntimeError(f"Failed to deploy helm chart. Run helm install manually and see why it fails")
            logger.info(helm_deploy.stdout)
            if not "STATUS: deployed" in helm_deploy.stdout:
                logger.error(helm_deploy)
                raise RuntimeError("Failed to deploy helm chart. Run helm install manually and see why it fails")
        except subprocess.CalledProcessError as cpe:
            logger.error(f"Error deploying the SUT {cpe}")
            raise cpe
    
    def uninstall(self) -> None:
        """
        Uninstalls the helm chart
        """
        logger.info(f"Uninstalling the SUT's helm chart {self.name}")
        subprocess.run(["helm", "uninstall", self.name, "-n", self.sut_config.namespace])
