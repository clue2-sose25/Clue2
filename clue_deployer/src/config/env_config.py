from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field
from pathlib import Path
from functools import lru_cache


class EnvConfig(BaseSettings):
    """
    Environment configuration for the Clue Deployer application.
    """

    SUT_CONFIGS_PATH: Path = Path("/app/sut_configs")
    CLUE_CONFIG_PATH: Path = Path("/app/clue-config.yaml")
    RESULTS_PATH: Path = Path("/app/data")
    LOG_LEVEL: str = "INFO"

    SUT_NAME: str|None = Field(default=None, env="SUT_NAME")  # Environment variable for SUT name
    EXPERIMENT_NAME: str|None = Field(default=None, env="EXPERIMENT_NAME")  


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
        Constructs the SUT configuration path based on the SUT_NAME.
        """
        if self.SUT_NAME:
            return self.SUT_CONFIGS_PATH / f"{self.SUT_NAME}.yaml"
        else:
            raise ValueError("SUT_NAME must be set to construct SUT_CONFIG_PATH.")


