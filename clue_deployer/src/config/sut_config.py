from pydantic import Field, computed_field, field_validator, ValidationInfo
from pydantic_settings import BaseSettings
from pathlib import Path
import yaml

from clue_deployer.src.config.helm_replacement import HelmReplacement

  
class SUTConfig(BaseSettings):
    """
    Configuration class for the System Under Test (SUT) using pydantic's BaseSettings.
    """
    sut_path: Path
    sut_git_repo: str
    namespace: str
    target_service_name: str
    application_endpoint_path: str
    default_resource_limits: dict[str, int]
    workload_settings: dict[str, str]
    timeout_duration: int
    wait_before_workloads: int
    wait_after_workloads: int
    helm_chart_path: Path
    # The path to the Helm chart directory if the chart is not in the SUT directory
    timeout_for_services_ready: int = Field(default=180)
    helm_chart_repo: str = Field(default="")
    helm_dependencies_from_chart: bool = Field(default=False)
    values_yaml_name: str = Field(default="values.yaml")
    infrastructure_namespaces: list[str] = Field(default_factory=list)  
    sut: str = Field(default="")
    helm_replacements: list[HelmReplacement] = Field(default_factory=list)

    class Config:
        # Allow environment variable overrides
        env_prefix = "SUT_"
    
    @field_validator("sut")
    def get_sut(cls, sut: str, info: ValidationInfo) -> str:
        """
        Set the SUT to the stem of the sut_path if not provided.
        """
        if sut:
            return sut
        sut_path = info.data.get("sut_path")
        if sut_path:
            return sut_path.stem

    @computed_field
    @property
    def target_host(self) -> str:
        """
        Constructs the target host URL 
        """
        # Ensure application_endpoint_path starts with a slash if it's not guaranteed
        path = self.application_endpoint_path
        if not path.startswith("/"):
            path = "/" + path
         
        return f"http://{self.target_service_name}{self.application_endpoint_path}"

    @classmethod
    def load_from_yaml(cls, sut_config_path) -> "SUTConfig":
        """
        Load configuration from the YAML file specified by the global SUT_CONFIG_PATH.
        """
        with open(sut_config_path, 'r') as file:
            full_data = yaml.safe_load(file)
            
            # Extract config section
            config_data = full_data.get('config', {})
            
            # Add helm_replacements from the root level if they exist
            if 'helm_replacements' in full_data:
                config_data['helm_replacements'] = full_data['helm_replacements']
            
            return cls(**config_data)