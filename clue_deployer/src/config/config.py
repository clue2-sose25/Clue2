from __future__ import annotations
from pathlib import Path

from clue_deployer.src.config.clue_config import ClueConfig
from clue_deployer.src.config.env_config import EnvConfig
from clue_deployer.src.config.experiment_configs import ExperimentsConfig
from clue_deployer.src.config.services import ServicesConfig
from clue_deployer.src.config.sut_config import SUTConfig

class Config:
    """
    Manage and provide access to all configurations.
    """

    def __init__(self, sut_config: Path = None, clue_config: Path = None):
        """
        Load all configurations from the given paths.

        """
        env_config = EnvConfig.get_env_config()
        if sut_config is None:
            sut_config = env_config.SUT_CONFIG_PATH
        if clue_config is None:
            clue_config = env_config.CLUE_CONFIG_PATH
        self.env_config = env_config
        self.clue_config = ClueConfig.load_from_yaml(clue_config)
        self.experiments_config = ExperimentsConfig.load_from_yaml(sut_config)
        self.services_config = ServicesConfig.load_from_yaml(sut_config)
        self.sut_config = SUTConfig.load_from_yaml(sut_config)


    @classmethod
    def get_instance(cls) -> "Config":
        """
        Get the singleton instance of the Config.
        """
        if cls._instance is None:
            raise RuntimeError("ConfigManager has not been initialized. Call ConfigManager(sut_config, clue_config) first.")
        return cls._instance
    
# Export a global config for other files
CONFIGS = Config()
ENV_CONFIG = CONFIGS.env_config