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
        print(f"🚀 setting up hpa scaling")
        if (exp.autoscaling == ScalingExperimentSetting.MEMORYBOUND):
            self._setup_mem_autoscaling()
        elif exp.autoscaling == ScalingExperimentSetting.CPUBOUND:
            self._setup_cpu_autoscaleing()
        else:
            raise NotImplementedError(
                "multi-mode autoscaling not implemented in cluster yet"
            )

    def _setup_autoscaling(self, hpa_creator):
        exp = self.experiment

        apps = kubernetes.client.AppsV1Api()
        
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
                hpa_creator(stateful_set.metadata.name, exp.namespace)
            except kubernetes.client.rest.ApiException as e:
                if e.status == 409:
                    print(f"HPA for {stateful_set.metadata.name} already exists")
                else:
                    raise e

    def _setup_mem_autoscaling(self):
        exp = self.experiment
        hpas = kubernetes.client.AutoscalingV2Api()

        def _mem_hpa_creator(target_name:str, namespace:str):
            hpas.create_namespaced_horizontal_pod_autoscaler(
                namespace=namespace,
                body=kubernetes.client.V2HorizontalPodAutoscaler(
                    metadata=kubernetes.client.V1ObjectMeta(
                        name=target_name, namespace=namespace
                    ),
                    spec=kubernetes.client.V2HorizontalPodAutoscalerSpec(
                        scale_target_ref=kubernetes.client.V2CrossVersionObjectReference(
                            api_version="apps/v1",
                            kind="StatefulSet",
                            name=target_name
                        ),
                        min_replicas=1,
                        max_replicas=exp.max_autoscale,
                        behavior=kubernetes.client.V2HorizontalPodAutoscalerBehavior(
                            scale_down=kubernetes.client.V2HPAScalingRules(
                                policies=[
                                    #quick scaleup (with stabilization)
                                    kubernetes.client.V2HPAScalingPolicy(
                                        value=1,
                                        period_seconds=60,
                                        type="Pods",
                                    ),
                                ],
                                stabilization_window_seconds=120
                            ),
                            scale_up=kubernetes.client.V2HPAScalingRules(
                                stabilization_window_seconds=30,
                                 policies=[
                                    kubernetes.client.V2HPAScalingPolicy(
                                        value=3,
                                        period_seconds=15,
                                        type="Pods",
                                    ),
                                ],
                            ),
                        ),
                        metrics=[
                            kubernetes.client.V2MetricSpec(
                                resource=kubernetes.client.V2ResourceMetricSource(
                                    name="memory",
                                    target=kubernetes.client.V2MetricTarget(
                                        average_utilization=80,
                                        type="Utilization",
                                    )
                                ),
                                type="Resource"
                            )
                        ],
                    )
                )
            )

        self._setup_autoscaling(_mem_hpa_creator)

    def _setup_cpu_autoscaleing(self):
        hpas = kubernetes.client.AutoscalingV1Api()
        def _cpu_hap_creator(target_name:str, namespace:str):
            resp = hpas.create_namespaced_horizontal_pod_autoscaler(
                body=kubernetes.client.V1HorizontalPodAutoscaler(
                    metadata=kubernetes.client.V1ObjectMeta(
                        name=target_name, namespace=namespace
                    ),
                    spec=kubernetes.client.V1HorizontalPodAutoscalerSpec(
                        scale_target_ref=kubernetes.client.V1CrossVersionObjectReference(
                            api_version="apps/v1",
                            kind="StatefulSet",
                            name=target_name,
                        ),
                        min_replicas=1,
                        max_replicas=3,
                        target_cpu_utilization_percentage=80,
                    ),
                ),
                namespace=namespace,
            )

        self._setup_autoscaling(_cpu_hap_creator)

    def cleanup_autoscaling(self):
        hpas = kubernetes.client.AutoscalingV1Api()
        _hpas = hpas.list_namespaced_horizontal_pod_autoscaler(self.experiment.namespace)
        for stateful_set in _hpas.items:
            hpas.delete_namespaced_horizontal_pod_autoscaler(
                name=stateful_set.metadata.name, namespace=self.experiment.namespace
            )
