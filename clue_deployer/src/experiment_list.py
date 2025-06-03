import copy

from dataclasses import dataclass
from clue_deployer.src.config import Config
from clue_deployer.src.experiment import Experiment
from clue_deployer.src.scaling_experiment_setting import ScalingExperimentSetting
from clue_deployer.src.experiment_workloads import Workload
from clue_deployer.src.experiment_environment import ExperimentEnvironment

@dataclass
class ExperimentList():
    experiments: list[Experiment]

    @staticmethod
    def load_experiments(config: Config, exp_name: str) -> "ExperimentList":
        """
        Load experiments from a YAML file and return an ExperimentList instance.
        If exp_name is 'all', returns all experiments; otherwise, filters by exp_name.
        """
        experiments_config = config.experiments_config
        experiments = []
        
        for exp in experiments_config.experiments:
            # Create an Experiment instance for each experiment in the YAML file
            experiment = Experiment(
                name=exp.name,
                target_branch=exp.target_branch,
                colocated_workload=exp.colocated_workload,  # TODO default False
                env=ExperimentEnvironment(config),
                autoscaling=ScalingExperimentSetting.CPUBOUND,  # TODO customizable
                critical_services=exp.critical_services,
                config=config,
            )
            # Add experiment to list if exp_name is 'all' or matches experiment name
            if exp_name == "all" or exp.name == exp_name:
                experiments.append(experiment)
        
        return ExperimentList(experiments=experiments)
    
    def __iter__(self):
        """
        Make the ExperimentList class iterable by returning an iterator
        for the list of experiments.
        """
        return iter(self.experiments)

    def __repr__(self):
        """
        Return a string representation of the ExperimentList class.
        """
        return f"ExperimentList({self.experiments})"

    @staticmethod
    def _set_workload(exp: Experiment, workload: Workload) -> Experiment:
        new_ex = copy.deepcopy(exp)
        new_ex.env.set_workload(workload)
        return new_ex

    def add_workloads(self, workloads: list[Workload]) -> None:
        exps_with_workloads = []
        for w in workloads:
            for exp in self.experiments:
                exps_with_workloads.append(self._set_workload(exp,w))
        self.experiments = exps_with_workloads

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