from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field
from pathlib import Path


class EnvConfig(BaseSettings):
    """
    Environment configuration for the Clue Deployer application.
    """
    _instance: "EnvConfig" | None = None

    SUT_CONFIGS_PATH: Path = Path("/app/sut_configs")
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

    @classmethod
    def get_instance(cls) -> "EnvConfig":
        """
        Get the singleton instance of the EnvConfig.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

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