from typing import List
from pydantic import Field, computed_field, field_validator, ValidationInfo
from pydantic_settings import BaseSettings
from pathlib import Path
import yaml
from clue_deployer.src.models.helm_replacement import HelmReplacement
from clue_deployer.src.models.resource_limit import ResourceLimit
from clue_deployer.src.models.variant import Variant
from clue_deployer.src.models.workload import Workload

class SUTConfig(BaseSettings):
    """
    Configuration class for the System Under Test (SUT)
    """
    # SUT
    sut: str = Field(default="")
    sut_path: Path
    sut_git_repo: str
    # Helm
    helm_chart_path: Path
    helm_chart_repo: str = Field(default="") 
    helm_dependencies_from_chart: bool = Field(default=False)
    values_yaml_name: str = Field(default="values.yaml")
    # K8s namespace
    namespace: str
    infrastructure_namespaces: list[str] = Field(default_factory=list)
    target_service_name: str
    application_endpoint_path: str
    default_resource_limits: dict[str, int]
    # Timings
    wait_before_workloads: int
    wait_after_workloads: int
    timeout_for_services_ready: int = Field(default=180)    
    # The list of helm replacements
    helm_replacements: list[HelmReplacement] = Field(default_factory=list)
    # The list of variants
    variants: List[Variant]
    # The list of workloads
    workloads: List[Workload]
    # The list of resource limits
    resource_limits: list[ResourceLimit]

    class Config:
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
        return sut

    @computed_field
    @property
    def target_host(self) -> str:
        """
        Constructs the target host URL 
        """
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
            config_data = full_data.get('config', {})
            
            # Add children and convert dictionaries to model instances
            if 'helm_replacements' in full_data:
                config_data['helm_replacements'] = [
                    HelmReplacement(**item) if isinstance(item, dict) else item
                    for item in full_data['helm_replacements']
                ]
            
            if 'variants' in full_data:
                config_data['variants'] = [
                    Variant(**item) if isinstance(item, dict) else item
                    for item in full_data['variants']
                ]
            
            if 'resource_limits' in full_data:
                config_data['resource_limits'] = [
                    ResourceLimit(**item) if isinstance(item, dict) else item
                    for item in full_data['resource_limits']
                ]
            
            if 'workloads' in full_data:
                config_data['workloads'] = [
                    Workload(**item) if isinstance(item, dict) else item
                    for item in full_data['workloads']
                ]

            return cls(**config_data)