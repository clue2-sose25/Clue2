from experiment import Experiment
from scaling_experiment_setting import ScalingExperimentSetting

NUM_ITERATIONS = 1


# prometheus_url = "http://130.149.158.130:32426" # actual ip of prometheus node
# prometheus_url = "http://host.minikube.internal:9090" # for minikube usage
# prometheus_url = "http://192.168.1.219:9090"

# helm install prometheus prometheus-community/prometheus
prometheus_url = "http://localhost:9090" # minikube
# prometheus_url = "http://prometheus-server.default.svc.cluster.local" # minikube

namespace = "tea-bench"
scale = ScalingExperimentSetting.CPUBOUND


exps = [
    Experiment(
        name="baseline",
        target_branch="vanilla",
        # patches=[],
        namespace=namespace,
        colocated_workload=True,
        prometheus_url=prometheus_url,
        autoscaling=scale,
    ),
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
]