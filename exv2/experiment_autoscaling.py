import math

import kubernetes

from experiment import Experiment
from scaling_experiment_setting import ScalingExperimentSetting


class ExperimentAutoscaling:

    def __init__(self, experiment: Experiment):
        self.experiment = experiment

    def setup_autoscaling(self):
        """
        create a list of statefulsets to scale;
        for each statefulset: set memory and cpu limites/requests per service
        then create hpa for each statefulset with the given target based on the experiment setting
        """

        exp = self.experiment

        if (
                exp.autoscaling == ScalingExperimentSetting.MEMORYBOUND
                or exp.autoscaling == ScalingExperimentSetting.BOTH
        ):
            raise NotImplementedError(
                "memory bound autoscaling not implemented in cluster yet"
            )

        print(f"🚀 setting up hpa scaling")

        apps = kubernetes.client.AppsV1Api()
        hpas = kubernetes.client.AutoscalingV1Api()
        sets: kubernetes.client.V1StatefulSetList = apps.list_namespaced_stateful_set(
            exp.namespace
        )
        for stateful_set in sets.items:
            if stateful_set.metadata.name in exp.env.resource_limits:
                limit = exp.env.resource_limits[stateful_set.metadata.name]
            else:
                continue
            stateful_set.spec.template.spec.containers[0].resources = (
                kubernetes.client.V1ResourceRequirements(
                    requests={
                        "cpu": f'{limit["cpu"]}m',
                        "memory": f'{limit["memory"]}Mi',
                    },
                    limits={
                        "cpu": f'{int(math.floor(limit["cpu"] * 1.5))}m',
                        "memory": f'{int(math.floor(limit["memory"] * 1.5))}Mi',
                    },
                )
            )
            try:
                resp = apps.patch_namespaced_stateful_set(
                    stateful_set.metadata.name, exp.namespace, stateful_set
                )
                resp = hpas.create_namespaced_horizontal_pod_autoscaler(
                    body=kubernetes.client.V1HorizontalPodAutoscaler(
                        metadata=kubernetes.client.V1ObjectMeta(
                            name=stateful_set.metadata.name, namespace=exp.namespace
                        ),
                        spec=kubernetes.client.V1HorizontalPodAutoscalerSpec(
                            scale_target_ref=kubernetes.client.V1CrossVersionObjectReference(
                                api_version="apps/v1",
                                kind="StatefulSet",
                                name=stateful_set.metadata.name,
                            ),
                            min_replicas=1,
                            max_replicas=3,
                            target_cpu_utilization_percentage=80,
                        ),
                    ),
                    namespace=exp.namespace,
                )
            except kubernetes.client.rest.ApiException as e:
                if e.status == 409:
                    print(f"HPA for {stateful_set.metadata.name} already exists")
                else:
                    raise e

    def cleanup_autoscaling(self):
        hpas = kubernetes.client.AutoscalingV1Api()
        _hpas = hpas.list_namespaced_horizontal_pod_autoscaler(self.experiment.namespace)
        for stateful_set in _hpas.items:
            hpas.delete_namespaced_horizontal_pod_autoscaler(
                name=stateful_set.metadata.name, namespace=self.experiment.namespace
            )
