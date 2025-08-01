from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field, field_validator
from functools import lru_cache

class EnvConfig(BaseSettings):
    """
    Environment configuration for the Clue Deployer application.
    """
    # CLUE Configs
    SUT_CONFIGS_PATH: Path = Path("/app/sut_configs")
    CLUE_CONFIG_PATH: Path = Path("/app/clue-config.yaml")
    RESULTS_PATH: Path = Path("/app/data")
    LOG_LEVEL: str = "INFO"

    # Environment variables
    SUT: str|None = Field(default=None, env="SUT")  
    VARIANTS: list[str]|None = Field(default=None, env="VARIANTS")
    WORKLOADS: list[str]|None = Field(default=None, env="WORKLOADS")
    N_ITERATIONS: int|None = Field(default=1, env="N_ITERATIONS")
    DEPLOY_ONLY: bool|None = Field(default=False, env="DEPLOY_ONLY")
    # Grafana
    GRAFANA_USERNAME: str|None = Field(default="admin", env="GRAFANA_USERNAME")
    GRAFANA_PASSWORD: str|None = Field(default="prom-operator", env="GRAFANA_PASSWORD")
    GRAFANA_URL: str|None = Field(default="http://grafana.monitoring.svc.cluster.local:80", env="GRAFANA_URL")
    GRAFANA_PORT: str|None = Field(default="3000", env="GRAFANA_PORT")
    SETUP_GRAFANA_DASHBOARD: str|None = Field(default="false", env="SETUP_GRAFANA_DASHBOARD")

    model_config = SettingsConfigDict(
        env_file=".env",  # Load from .env file if present 
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra environment variables not defined in the model
        case_sensitive=False
    )
    
    #Workaround since pydantic does not support singleton pattern directly
    @lru_cache(maxsize=1)
    @staticmethod
    def get_env_config():
        return EnvConfig()
    
    @field_validator("VARIANTS", "WORKLOADS", mode="before")
    @classmethod
    def split_comma_separated(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @computed_field
    @property
    def SUT_CONFIG_PATH(self) -> Path:
        """
        Constructs the SUT configuration path based on the SUT.
        """
        if self.SUT:
            return self.SUT_CONFIGS_PATH / f"{self.SUT}.yaml"
        else:
            raise ValueError("SUT must be set to construct SUT_CONFIG_PATH.")
    
    def model_dump(self, **kwargs) -> dict:
        """Return a dictionary representation with Path objects converted to strings."""
        config_dict = super().model_dump(**kwargs)
        # Convert Path objects to strings for JSON serialization
        for key, value in config_dict.items():
            if isinstance(value, Path):
                config_dict[key] = str(value)
        return config_dict