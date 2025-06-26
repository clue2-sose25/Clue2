import copy

from dataclasses import dataclass
from clue_deployer.src.config import Config
from clue_deployer.src.models.variant import Variant
from clue_deployer.src.models.scaling_experiment_setting import ScalingExperimentSetting
from clue_deployer.src.experiment_workloads import Workload
from clue_deployer.src.experiment_environment import VariantEnvironment

@dataclass
class VariantsList():
    variants: list[Variant]

    @staticmethod
    def load_variants(config: Config, variant_name: str) -> "VariantsList":
        """
        Load variants from a YAML file and return an VariantsList instance.
        If variant_name is 'all', returns all variants; otherwise, filters by variant_name
        """
        variants_config = config.variants_config
        variants = []

        if variant_name == "all":
            names = None
        else:
            names = [n.strip() for n in variant_name.split(",") if n.strip()]
        
        for exp in variants_config.variants:
            # Create an Experiment instance for each experiment in the YAML file
            experiment = Variant(
                name=exp.name,
                target_branch=exp.target_branch,
                colocated_workload=exp.colocated_workload,  # TODO default False
                env=VariantEnvironment(config),
                autoscaling=exp.autoscaling,
                critical_services=exp.critical_services,
                config=config,
            )
            # Add experiment to list if exp_name is 'all' or matches experiment name
            if names is None or exp.name in names:
                variants.append(experiment)
        
        return VariantsList(variants=variants)
    
    def __iter__(self):
        """
        Make the ExperimentList class iterable by returning an iterator
        for the list of experiments.
        """
        return iter(self.variants)

    def __repr__(self):
        """
        Return a string representation of the ExperimentList class.
        """
        return f"ExperimentList({self.variants})"

    @staticmethod
    def _set_workload(exp: Variant, workload: Workload) -> Variant:
        new_ex = copy.deepcopy(exp)
        new_ex.env.set_workload(workload)
        return new_ex

    def add_workloads(self, workloads: list[Workload]) -> None:
        exps_with_workloads = []
        for w in workloads:
            for exp in self.variants:
                exps_with_workloads.append(self._set_workload(exp,w))
        self.variants = exps_with_workloads

    def sort(self):
        """
        Sort the experiments based on their names.
        """
        self.variants.sort(key=lambda exp: "_".join([exp.target_branch, exp.name]))


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