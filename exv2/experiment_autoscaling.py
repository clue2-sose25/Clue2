import math
from os import path
import subprocess
import experiment
from scaling_experiment_setting import ScalingExperimentSetting
from experiment_environment import ExperimentEnvironment
from experiment import Experiment
import kubernetes

class ExperimentAutoscaling:


    def __init__(self, experiment: experiment.Experiment):
        self.experiment = experiment

    def setup_autoscaleing(self):
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

        client = self.docker_client

        print(f"🚀 setting up hpa scaling")

        apps = kubernetes.client.AppsV1Api()
        hpas = kubernetes.client.AutoscalingV1Api()
        sets: kubernetes.client.V1StatefulSetList = apps.list_namespaced_stateful_set(
            exp.namespace
        )
        for set in sets.items:
            if set.metadata.name in ExperimentEnvironment().resource_limits:
                limit = ExperimentEnvironment().resource_limits[set.metadata.name]
            else:
                continue
            set.spec.template.spec.containers[0].resources = (
                client.V1ResourceRequirements(
                    requests={
                        "cpu": f'{limit["cpu"]}m',
                        "memory": f'{limit["memory"]}Mi',
                    },
                    limits={
                        "cpu": f'{int(math.floor(limit["cpu"]*1.5))}m',
                        "memory": f'{int(math.floor(limit["memory"]*1.5))}Mi',
                    },
                )
            )
            try:
                resp = apps.patch_namespaced_stateful_set(
                    set.metadata.name, exp.namespace, set
                )
                resp = hpas.create_namespaced_horizontal_pod_autoscaler(
                    body=client.V1HorizontalPodAutoscaler(
                        metadata=client.V1ObjectMeta(
                            name=set.metadata.name, namespace=exp.namespace
                        ),
                        spec=client.V1HorizontalPodAutoscalerSpec(
                            scale_target_ref=client.V1CrossVersionObjectReference(
                                api_version="apps/v1",
                                kind="StatefulSet",
                                name=set.metadata.name,
                            ),
                            min_replicas=1,
                            max_replicas=3,
                            target_cpu_utilization_percentage=80,
                        ),
                    ),
                    namespace=exp.namespace,
                )
            except kubernetes.ApiException as e:
                if e.status == 409:
                    print(f"HPA for {set.metadata.name} already exsist")
                else:
                    raise e


    def cleanup_autoscaling(self: Experiment):
        hpas = kubernetes.client.AutoscalingV1Api()
        _hpas = hpas.list_namespaced_horizontal_pod_autoscaler(self.namespace)
        for set in _hpas.items:
            hpas.delete_namespaced_horizontal_pod_autoscaler(
                name=set.metadata.name, namespace=self.namespace
            )
