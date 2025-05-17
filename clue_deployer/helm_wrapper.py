
import subprocess

from clue_deployer.config import Config
from clue_deployer.scaling_experiment_setting import ScalingExperimentSetting


class HelmWrapper():
    
    def __init__(self, config: Config, autoscaling: bool):
        self.clue_config = config.clue_config
        self.sut_config = config.sut_config
        self.autoscaling = autoscaling
        self.values_file_full_path = self.sut_config.helm_chart_path / self.sut_config.values_yaml_name
        self.name = self.sut_config.sut_path.name

    def update_helm_chart(self) -> dict:
        """Loads the values.yaml file."""
        if not self.values_file_full_path.exists():
            raise FileNotFoundError(f"Values file not found at {self.values_file_full_path}")
        
        with open(self.values_file_full_path, "r") as f:
            values = f.read()
        
        values = values.replace("descartesresearch", self.clue_config.docker_registry_address)
        # ensure we only run on nodes that we can observe - set nodeSelector to scaphandre
        values = values.replace(
            r"nodeSelector: {}", r'nodeSelector: {"scaphandre": "true"}'
        )
        values = values.replace("pullPolicy: IfNotPresent", "pullPolicy: Always")
        values = values.replace(r'tag: ""', r'tag: "latest"')
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
        with open(self.values_file_full_path, "w") as f:
            f.write(values)
        
        return values
        
    def deploy(self) -> None:
        """deploys the helm chart"""
        try:
            print(f"deploying helm chart in {self.sut_config.helm_chart_path}")
            helm_deploy = subprocess.check_output(
                ["helm", "install", self.name, "-n", self.sut_config.namespace, "."],
                cwd=self.sut_config.helm_chart_path,
            )
            helm_deploy = helm_deploy.decode("utf-8")
            print(helm_deploy)
            if not "STATUS: deployed" in helm_deploy:
                print(helm_deploy)
                raise RuntimeError("failed to deploy helm chart. Run helm install manually and see why it fails")
        except subprocess.CalledProcessError as cpe:
            print(cpe)