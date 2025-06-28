from __future__ import annotations
from pathlib import Path

from clue_deployer.src.configs.clue_config import ClueConfig
from clue_deployer.src.configs.env_config import EnvConfig
from clue_deployer.src.configs.sut_config import SUTConfig

class Configs:
    """
    Manage and provide access to all configurations.
    """

    def __init__(self, sut_config_path: Path = None, clue_config_path: Path = None):
        """
        Load all configurations from the given paths, with variants loaded inplace.
        """
        # Config paths
        env_config = EnvConfig.get_env_config()
        if sut_config_path is None:
            sut_config_path = env_config.SUT_CONFIG_PATH
        if clue_config_path is None:
            clue_config_path = env_config.CLUE_CONFIG_PATH
        # Set configs
        self.env_config = env_config
        self.clue_config = ClueConfig.load_from_yaml(clue_config_path)
        self.sut_config = SUTConfig.load_from_yaml(sut_config_path)


    @classmethod
    def get_instance(cls) -> "Configs":
        """
        Get the singleton instance of the Config.
        """
        if cls._instance is None:
            raise RuntimeError("ConfigManager has not been initialized. Call ConfigManager(sut_config, clue_config) first.")
        return cls._instance
    
# Export a global config for other files
CONFIGS = Configs()
ENV_CONFIG = CONFIGS.env_config
CLUE_CONFIG = CONFIGS.clue_config
SUT_CONFIG = CONFIGS.sut_config