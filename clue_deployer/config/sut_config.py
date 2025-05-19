from pydantic import Field, computed_field
from pydantic_settings import BaseSettings
from pathlib import Path
import yaml

# Global constant for the YAML configuration file path
  


class SUTConfig(BaseSettings):
    """
    Configuration class for the System Under Test (SUT) using pydantic's BaseSettings.
    """
    sut_path: Path
    namespace: str
    #target_host: str
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

    class Config:
        # Allow environment variable overrides
        env_prefix = "SUT_"
    
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
