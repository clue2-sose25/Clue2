import copy

from dataclasses import dataclass
from config import Config

from experiment import Experiment
from scaling_experiment_setting import ScalingExperimentSetting
from experiment_workloads import Workload
from experiment_environment import ExperimentEnvironment

@dataclass
class ExperimentList():
    experiments: list[Experiment]

    @staticmethod
    def load_experiments(config: Config) -> "ExperimentList":
        """
        Load experiments from a YAML file and return an ExperimentList instance.
        """
        
        clue_config = config.clue_config
        sut_config = config.sut_config
        experiments_config = config.experiments_config
        
        experiments = []
        for exp in experiments_config.experiments:
            # Create an Experiment instance for each experiment in the YAML file
            experiment = Experiment(
                name=exp.name,
                target_branch=exp.target_branch,
                namespace=clue_config.namespace,
                colocated_workload=exp.colocated_workload, #TODO default False
                prometheus_url=clue_config.prometheus_url,
                env=ExperimentEnvironment(config),
                autoscaling=ScalingExperimentSetting.CPUBOUND, #TODO customizable,
                critical_services=exp.critical_services,
                target_host=sut_config.target_host,
                infrastrcutre_namespaces=sut_config.infrastructure_namespaces,
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