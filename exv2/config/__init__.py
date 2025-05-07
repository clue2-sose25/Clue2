from pathlib import Path
from clue_config import ClueConfig
from experiment_configs import ExperimentsConfig, Experiment
from services import ServicesConfig
from sut_config import SUTConfig

CLUE_CONFIG_PATH = Path("..").joinpath("clue_config.yaml")

#SUT_CONFIGS_DIR = Path("..").joinpath("..").joinpath("sut_configs")

def load_configs(sut_config: Path, 
                 clue_config: Path = CLUE_CONFIG_PATH) -> tuple[ClueConfig,
                                                                ExperimentsConfig,
                                                                ServicesConfig,
                                                                SUTConfig]:
    """
    Load the configuration files from the given paths.
    """
    return ClueConfig.load_from_yaml(clue_config), \
           ExperimentsConfig.load_from_yaml(sut_config), \
           ServicesConfig.load_from_yaml(sut_config), \
           SUTConfig.load_from_yaml(sut_config)