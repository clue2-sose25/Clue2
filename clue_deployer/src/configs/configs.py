from pathlib import Path
import os
from clue_deployer.src.configs.clue_config import ClueConfig
from clue_deployer.src.configs.env_config import EnvConfig
from clue_deployer.src.configs.sut_config import SUTConfig

class Configs:
    """
    Manage and provide access to all configurations.
    """

    def __init__(self, sut_config_path: Path | None = None, clue_config_path: Path | None = None):
        """Load all configurations from the given paths."""
        self.env_config = EnvConfig.get_env_config()
        if clue_config_path is None:
            clue_config_path = self.env_config.CLUE_CONFIG_PATH
        self.clue_config = ClueConfig.load_from_yaml(clue_config_path)

        self.sut_config = None
        if sut_config_path is None:
            try:
                sut_config_path = self.env_config.SUT_CONFIG_PATH
            except Exception as exc:
                if os.getenv("DEPLOY_AS_SERVICE", "false").lower() == "true":
                    # Service mode may start without a SUT config
                    self._init_error = str(exc)
                    return
                raise

        if not Path(sut_config_path).is_file():
            if os.getenv("DEPLOY_AS_SERVICE", "false").lower() == "true":
                self._init_error = f"SUT config not found: {sut_config_path}"
                return
            raise FileNotFoundError(f"SUT config not found: {sut_config_path}")

        self.sut_config = SUTConfig.load_from_yaml(sut_config_path)

    def model_dump(self) -> dict:
        """Return a dictionary representation of all configurations."""
        return {
            "env_config": self.env_config.model_dump(),
            "clue_config": self.clue_config.model_dump(),
            "sut_config": self.sut_config.model_dump()
        }

    @classmethod
    def get_instance(cls) -> "Configs":
        """
        Get the singleton instance of the Config.
        """
        if cls._instance is None:
            raise RuntimeError("ConfigManager has not been initialized. Call ConfigManager(sut_config, clue_config) first.")
        return cls._instance

# Export a global config for other files. When running as a service without
# a SUT configuration the initialization is skipped so the backend can start.
CONFIGS: Configs | None = None
ENV_CONFIG = EnvConfig.get_env_config()
CLUE_CONFIG = None
SUT_CONFIG = None

try:
    CONFIGS = Configs()
    CLUE_CONFIG = CONFIGS.clue_config
    SUT_CONFIG = CONFIGS.sut_config
    ENV_CONFIG = CONFIGS.env_config
except Exception as exc:
    if os.getenv("DEPLOY_AS_SERVICE", "false").lower() == "true":
        print(f"[CONFIGS] starting without SUT config: {exc}")
    else:
        raise