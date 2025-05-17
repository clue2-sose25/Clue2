import yaml
import subprocess

from config import SUTConfig
from functools import cached_property


class HelmWrapper():
    
    def __init__(self, config: SUTConfig):
        self.sut_config = config
        self.values_file_full_path = self.sut_config.helm_chart_path / self.sut_config.values_yaml_name
        self.values = self._load_values() # Load on initialization
        self.name = self.sut_config.sut_path.name

    def _load_values(self) -> dict:
        """Loads the values.yaml file."""
        if not self.values_file_full_path.exists():
            raise FileNotFoundError(f"Values file not found at {self.values_file_full_path}")
        try:
            with open(self.values_file_full_path, "r") as f:
                values = yaml.safe_load(f)
            return values
        except yaml.YAMLError as e:
            raise RuntimeError(f"Error loading YAML file: {self.values_file_full_path}") from e
        
    def update_values(self, **kwargs):
        """Updates the values dictionary with new values."""
        for key, value in kwargs.items():
            if key in self.values:
                self.values[key] = value
            else:
                raise KeyError(f"Key '{key}' not found in values.yaml")
        
        # Save the updated values back to the file
        with open(self.values_file_full_path, "w") as f:
            yaml.dump(self.values, f)
    
    def deploy(self):
        """deploys the helm chart"""
        try:
            helm_deploy = subprocess.check_output(
                ["helm", "install", self.name, "-n", self.experiment.namespace, "."],
                cwd=self.sut_config.helm_chart_path,
            )
            helm_deploy = helm_deploy.decode("utf-8")
            if not "STATUS: deployed" in helm_deploy:
                print(helm_deploy)
                raise RuntimeError("failed to deploy helm chart. Run helm install manually and see why it fails")
        except subprocess.CalledProcessError as cpe:
            print(cpe)