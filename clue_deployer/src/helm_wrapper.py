
import subprocess
from pathlib import Path
import tempfile
import shutil
from logger import logger
from clue_deployer.src.config import Config
from clue_deployer.src.scaling_experiment_setting import ScalingExperimentSetting


class HelmWrapper():
    
    def __init__(self, config: Config, autoscaling: bool = True):
        self.clue_config = config.clue_config
        self.sut_config = config.sut_config
        self.autoscaling = autoscaling
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
    
    def _cleanup_temp_chart_copy(self):
        """Cleans up the temporary chart directory."""
        if self._temp_dir_context:
            print(f"Cleaning up temporary chart directory: {self._temp_dir_context.name}")
            self._temp_dir_context.cleanup()
            self._temp_dir_context = None
        self.active_chart_path = None
        self.active_values_file_path = None

    def __enter__(self):
        """Support using HelmWrapper as a context manager for temp dir handling."""
        self._create_temp_chart_copy()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure cleanup when exiting context."""
        self._cleanup_temp_chart_copy()

    def update_helm_chart(self) -> dict:
        """Loads the values.yaml file."""
        if not self.active_values_file_path.exists():
            raise FileNotFoundError(f"Values file not found at {self.active_values_file_path}")
        
        with open(self.active_values_file_path, "r") as f:
            values = f.read()
        
        values = values.replace("descartesresearch", self.clue_config.docker_registry_address)
        # ensure we only run on nodes that we can observe - set nodeSelector to scaphandre
        values = values.replace(
            r"nodeSelector: {}", r'nodeSelector: {"scaphandre": "true"}'
        )
        values = values.replace("pullPolicy: IfNotPresent", "pullPolicy: Always")
        values = values.replace(r'tag: ""', r'tag: "vanilla"')
        if self.autoscaling:
            values = values.replace(r"enabled: false", "enabled: true")
            # values = values.replace(r"clientside_loadbalancer: false",r"clientside_loadbalancer: true")
            if self.autoscaling == ScalingExperimentSetting.MEMORYBOUND:
                values = values.replace(
                    r"targetCPUUtilizationPercentage: 80",
                    r"# targetCPUUtilizationPercentage: 80",
                )
                values = values.replace(
                    r"# targetMemoryUtilizationPercentage: 80",
                    r"targetMemoryUtilizationPercentage: 80",
                )
            elif self.autoscaling == ScalingExperimentSetting.BOTH:
                values = values.replace(
                    r"targetMemoryUtilizationPercentage: 80",
                    r"targetMemoryUtilizationPercentage: 80",
                )
        with open(self.active_values_file_path, "w") as f:
            f.write(values)
        
        return values
        
    def deploy(self) -> None:
        """deploys the helm chart"""
        if self.active_chart_path is None:
            raise RuntimeError("Temporary chart path not set. Did you call _create_temp_chart_copy()?")
        try:
            print(f"deploying helm chart in {self.active_chart_path}")
            helm_deploy = subprocess.check_output(
                ["helm", "install", self.name, "-n", self.sut_config.namespace, "."],
                cwd=self.active_chart_path,
            )
            helm_deploy = helm_deploy.decode("utf-8")
            print(helm_deploy)
            if not "STATUS: deployed" in helm_deploy:
                print(helm_deploy)
                raise RuntimeError("failed to deploy helm chart. Run helm install manually and see why it fails")
        except subprocess.CalledProcessError as cpe:
            print(cpe)
    
    def uninstall(self) -> None:
        """uninstalls the helm chart"""
        print(f"uninstalling helm chart {self.name}")
        subprocess.run(["helm", "uninstall", self.name, "-n", self.sut_config.namespace])
