import math
import kubernetes
from clue_deployer.src.configs.configs import CLUE_CONFIG, SUT_CONFIG
from clue_deployer.src.models.variant import Variant
from clue_deployer.src.models.scaling_experiment_setting import ScalingExperimentSetting
from clue_deployer.src.logger import logger

class AutoscalingDeployer:

    def __init__(self, variant: Variant):
        self.variant = variant

    def setup_autoscaling(self):
        """
        Create a list of statefulsets to scale;
        for each statefulset: set memory and cpu limites/requests per service
        then create hpa for each statefulset with the given target based on the variant setting
        """
        logger.info(f"Setting up HPA scaling with setting {self.variant.autoscaling}...")
        if (self.variant.autoscaling == ScalingExperimentSetting.MEMORYBOUND):
            self._setup_mem_autoscaling()
        elif self.variant.autoscaling == ScalingExperimentSetting.CPUBOUND:
            self._setup_cpu_autoscaleing()
        elif self.variant.autoscaling == ScalingExperimentSetting.BOTH:
            self._setup_full_autoscaling()
        else:
            logger.error(f"Unknown autoscaling setting {self.variant.autoscaling}")
            raise ValueError(f"Unknown autoscaling setting {self.variant.autoscaling}")

    def _setup_autoscaling(self, hpa_creator):
        apps = kubernetes.client.AppsV1Api()
        sets: kubernetes.client.V1StatefulSetList = apps.list_namespaced_stateful_set(SUT_CONFIG.namespace)
        for stateful_set in sets.items:
            if stateful_set.metadata.name in SUT_CONFIG.resource_limits:
                limit = SUT_CONFIG.resource_limits[stateful_set.metadata.name].limit
            else:
                limit = SUT_CONFIG.default_resource_limits
            stateful_set.spec.template.spec.containers[0].resources = (
                kubernetes.client.V1ResourceRequirements(
                    requests={
                        "cpu": f'{limit["cpu"]}m',
                        "memory": f'{limit["memory"]}Mi',
                    },
                    limits={
                        "cpu": f'{int(math.floor(limit["cpu"] * 1.3))}m',
                        "memory": f'{int(math.floor(limit["memory"] * 1.3))}Mi',
                    },
                )
            )
            try:
                _ = apps.patch_namespaced_stateful_set(
                    stateful_set.metadata.name, SUT_CONFIG.namespace, stateful_set
                )
                if stateful_set.metadata.name in SUT_CONFIG.services:
                    hpa_creator(stateful_set.metadata.name, SUT_CONFIG.namespace)
            except kubernetes.client.rest.ApiException as e:
                if e.status == 409:
                    logger.error(f"HPA for {stateful_set.metadata.name} already exists")
                else:
                    raise e
        logger.info("Successfully setup autoscaling")

    def _setup_mem_autoscaling(self):
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
                        max_replicas=self.variant.max_autoscale,
                        behavior=kubernetes.client.V2HorizontalPodAutoscalerBehavior(
                            scale_down=kubernetes.client.V2HPAScalingRules(
                                policies=[
                                    # Quick scale up (with stabilization)
                                    kubernetes.client.V2HPAScalingPolicy(
                                        value=1,
                                        period_seconds=30,
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
                                        average_utilization=CLUE_CONFIG.target_utilization,
                                        type="Utilization",
                                    )
                                ),
                                type="Resource"
                            )
                        ],
                    )
                )
            )
        logger.info("Created a MEM autoscaler")
        self._setup_autoscaling(_mem_hpa_creator)

    def _setup_cpu_autoscaleing(self):
        hpas = kubernetes.client.AutoscalingV1Api()
        def _cpu_hap_creator(target_name:str, namespace:str):
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
                        max_replicas=self.variant.max_autoscale,
                        behavior=kubernetes.client.V2HorizontalPodAutoscalerBehavior(
                            scale_down=kubernetes.client.V2HPAScalingRules(
                                policies=[
                                    # Quick scale up (with stabilization)
                                    kubernetes.client.V2HPAScalingPolicy(
                                        value=1,
                                        period_seconds=30,
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
                                    name="cpu",
                                    target=kubernetes.client.V2MetricTarget(
                                        average_utilization=CLUE_CONFIG.target_utilization,
                                        type="Utilization",
                                    )
                                ),
                                type="Resource"
                            ),
                        ],
                    )
                )
            )
        logger.info("Created a CPU autoscaler")
        self._setup_autoscaling(_cpu_hap_creator)
        

    def _setup_full_autoscaling(self):
        hpas = kubernetes.client.AutoscalingV1Api()
        def _full_hpa_creator(target_name:str, namespace:str):
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
                        max_replicas=self.variant.max_autoscale,
                        behavior=kubernetes.client.V2HorizontalPodAutoscalerBehavior(
                            scale_down=kubernetes.client.V2HPAScalingRules(
                                policies=[
                                    # Quick scale up (with stabilization)
                                    kubernetes.client.V2HPAScalingPolicy(
                                        value=1,
                                        period_seconds=30,
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
                                    name="cpu",
                                    target=kubernetes.client.V2MetricTarget(
                                        average_utilization=CLUE_CONFIG.target_utilization,
                                        type="Utilization",
                                    )
                                ),
                                type="Resource"
                            ),
                            kubernetes.client.V2MetricSpec(
                                resource=kubernetes.client.V2ResourceMetricSource(
                                    name="memory",
                                    target=kubernetes.client.V2MetricTarget(
                                        average_utilization=CLUE_CONFIG.target_utilization,
                                        type="Utilization",
                                    )
                                ),
                                type="Resource"
                            )
                        ],
                    )
                )
            )
        logger.info("Created a FULL autoscaler")
        self._setup_autoscaling(_full_hpa_creator)