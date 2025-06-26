from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field
from pathlib import Path
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
    VARIANTS: str|None = Field(default=None, env="VARIANTS")
    WORKLOADS: str|None = Field(default=None, env="WORKLOADS")
    DEPLOY_ONLY: bool|None = Field(default=False, env="DEPLOY_ONLY")  


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


