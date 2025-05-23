from pydantic import Field, computed_field, field_validator, ValidationInfo
from pydantic_settings import BaseSettings
from pathlib import Path
import yaml

# Global constant for the YAML configuration file path
  


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
    tags: list[str]
    helm_chart_path: Path
    values_yaml_name: str = Field(default="values.yaml")
    infrastructure_namespaces: list[str] = Field(default_factory=list)  
    num_iterations: int = Field(default=1)
    sut_name: str = Field(default="")

    class Config:
        # Allow environment variable overrides
        env_prefix = "SUT_"
    
    @field_validator("sut_name")
    def get_sut_name(cls, sut_name: str, info: ValidationInfo) -> str:
        """
        Set the sut_name to the stem of the sut_path if not provided.
        """
        if sut_name:
            return sut_name
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
            data = yaml.safe_load(file).get('config', {})
            return cls(**data)
