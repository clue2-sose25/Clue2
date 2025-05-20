from __future__ import annotations
from pathlib import Path
from .clue_config import ClueConfig
from .experiment_configs import ExperimentsConfig
from .services import ServicesConfig
from .sut_config import SUTConfig



class Config:
    """
    Singleton class to manage and provide access to all configurations.
    """
    _instance: Config | None = None

    def __new__(cls, sut_config: Path, clue_config: Path):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialize(sut_config, clue_config)
        return cls._instance

    def _initialize(self, sut_config: Path, clue_config: Path):
        """
        Load all configurations from the given paths.
        """
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