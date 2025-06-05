import os
from clue_deployer.src.deploy import ExperimentDeployer
from pathlib import Path
from clue_deployer.src.experiment_list import ExperimentList
from clue_deployer.src.config import Config
from clue_deployer.service.status_manager import StatusManager, Phase

# Get the root directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = "/app/clue-config.yaml"
SUT_NAME = os.environ.get("SUT_NAME")
EXP_NAME = os.environ.get("EXPERIMENT_NAME")
SUT_CONFIG_PATH = f"sut_configs/{SUT_NAME}.yaml"
RUN_CONFIG = Config(SUT_CONFIG_PATH, CONFIG_PATH)


def available_suts():
    """
    Reads the 'sut_configs' folder and returns a list of available SUT names.
    """
    sut_configs_path = Path("/app/sut_configs")
    if not sut_configs_path.exists():
        raise FileNotFoundError(f"SUT configs folder not found: {sut_configs_path}")
    # Get all YAML files in the 'sut_configs' folder
    sut_files = [f.stem for f in sut_configs_path.glob("*.yaml")]
    return sut_files


def run():
    # Check if SUT_NAME is valid
    available_suts_list = available_suts()
    if SUT_NAME not in available_suts_list:
        print(f"Invalid SUT name: '{SUT_NAME}'")
        print(f"Available SUTs: {available_suts_list}")
        return
    
    # Set the status to preparing
    StatusManager.set(Phase.PREPARING_CLUSTER, "Preparing the cluster...")
    # Get the experiment object
    experiment_list = ExperimentList.load_experiments(RUN_CONFIG, EXP_NAME)
    experiments = [e for e in experiment_list if e.name == EXP_NAME]
    if not len(experiments):
        raise ValueError(f"Invalid experiment name for {SUT_NAME}. Available experiments " + str([e.name for e in experiment_list]))
    else:   
        experiment = experiments[0]
    # Deploy the experiment, without the workload generator
    deployer = ExperimentDeployer(experiment, RUN_CONFIG)
    deployer.execute_deployment()

if __name__ == "__main__":
    run()