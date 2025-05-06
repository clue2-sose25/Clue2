import yaml
import copy

from pydantic import BaseModel
from dataclasses import dataclass
from pathlib import Path

from experiment import Experiment
from scaling_experiment_setting import ScalingExperimentSetting
from experiment_workloads import Workload

NUM_ITERATIONS = 1

CONFIGS_DIR = Path("..").joinpath("cfg")
EXPERIMENT_LIST = CONFIGS_DIR.joinpath("experiment_config.yaml")
EXPERIMENT_CONFIG = CONFIGS_DIR.joinpath("experiments.yaml")

class Config(BaseModel):
    prometheus_url: str
    namespace: str
    target_host: str

    @classmethod
    def load_from_yaml(cls, config_path: Path = EXPERIMENT_CONFIG) -> "Config":
        with open(config_path, 'r') as file:
            cfg = yaml.safe_load(file).get('config', {})
        return cls(**cfg)

@dataclass
class ExperimentList():
    experiments: list[Experiment]

    @staticmethod
    def load_experiments(experiments_path : Path = EXPERIMENT_LIST, config_path : Path = EXPERIMENT_CONFIG):
        """
        Load experiments from a YAML file and return an ExperimentList instance.
        """
        #load config
        config = Config.load_from_yaml(config_path)
        #load experiments
        with open(experiments_path, 'r') as file:
            data = yaml.safe_load(file)
            experiments = []
            for exp in data.get('experiments', []):
                # Create an Experiment instance for each experiment in the YAML file
                experiment = Experiment(
                    name=exp.get('name'),
                    target_branch=exp.get('target_branch'),
                    patches=exp.get('patches', []),
                    namespace=config.namespace,
                    colocated_workload=exp.get('colocated_workload', False),
                    prometheus_url=config.prometheus_url,
                    autoscaling=exp.get('autoscaling', ScalingExperimentSetting.CPUBOUND),
                    critical_services=exp.get('critical_services', []),
                    target_host=config.get('target_host'),
                    infrastrcutre_namespaces=exp.get('infrastrcutre_namespaces', [])
                )
                experiments.append(experiment)
        return ExperimentList(experiments=experiments)
    
    @staticmethod
    def _set_workload(exp: Experiment, workload: Workload):
        new_ex = copy.deepcopy(exp)
        new_ex.env.set_workload(workload)
        return new_ex

    def add_workloads(self, workloads: list[Workload]):
        exps = self.experiment_list.exps
        exps = []
        for w in workloads:
            for exp in self.experiment_list.exps:
                exps.append(self._set_workload(exp,w))
        return exps

    def sort(self):
        """
        Sort the experiments based on their names.
        """
        self.experiments.sort(key=lambda exp: "_".join([exp.target_branch, exp.name]))


# exps = [
#     Experiment(
#         name="baseline",
#         target_branch="vanilla",
#         # patches=[],
#         namespace=namespace,
#         colocated_workload=True,
#         prometheus_url=prometheus_url,
#         autoscaling=scale,
#     ),
    # Experiment(
    #     name="serverless",
    #     target_branch="serverless-auth",
    #     # patches=[],
    #     namespace=namespace,
    #     colocated_workload=True,
    #     prometheus_url=prometheus_url,
    #     autoscaling=scale,
    #     critical_services=["teastore-registry", "teastore-webui"],
    #     infrastrcutre_namespaces=["knative-serving"]
    # ),
    # Experiment(
    #     name="monolith",
    #     target_branch="monolith",
    #     namespace=namespace,
    #     colocated_workload=True,
    #     prometheus_url=prometheus_url,
    #     autoscaling=scale,
    #     critical_services=["teastore-all"],
    #     target_host="http://teastore-all/tools.descartes.teastore.webui",
    # ),
    # Experiment(
    #     name="jvm",
    #     target_branch="runtime-replacement",
    #     # patches=[],
    #     namespace=namespace,
    #     colocated_workload=True,
    #     prometheus_url=prometheus_url,
    #     autoscaling=scale,
    # ),
    # Experiment(
    #     name="norec",
    #     target_branch="service-reduction",
    #     # patches=[],
    #     namespace=namespace,
    #     colocated_workload=True,
    #     prometheus_url=prometheus_url,
    #     autoscaling=scale,
    # ),
    # Experiment(
    #     name="lessrec",
    #     target_branch="feature/lessrecs",
    #     # patches=[],
    #     namespace=namespace,
    #     colocated_workload=True,
    #     prometheus_url=prometheus_url,
    #     autoscaling=scale,
    # ),
    # Experiment(
    #     name="obs",
    #     target_branch="feature/object-storage",
    #     # patches=[],
    #     namespace=namespace,
    #     colocated_workload=True,
    #     prometheus_url=prometheus_url,
    #     autoscaling=scale,
    # ),
    # Experiment(
    #     name="dbopt",
    #     target_branch="feature/db-optimization",
    #     # patches=[],
    #     namespace=namespace,
    #     colocated_workload=True,
    #     prometheus_url=prometheus_url,
    #     autoscaling=scale,
    # ),
    # Experiment(
    #     name="car",
    #     target_branch="Carbon-Aware-Retraining",
    #     # patches=[],
    #     namespace=namespace,
    #     colocated_workload=True,
    #     prometheus_url=prometheus_url,
    #     autoscaling=scale,
    # ),
    # Experiment(
    #     name="sig",
    #     target_branch="ssg+api-gateway",
    #     # patches=[],
    #     namespace=namespace,
    #     colocated_workload=True,
    #     prometheus_url=prometheus_url,
    #     autoscaling=scale,
    # ),
#]