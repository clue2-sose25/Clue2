import platform
import threading

from datetime import datetime
from clue_deployer.src.models.variant import Variant
from psc.tracker import PodUsage
from psc import ResourceTracker, NodeUsage
from clue_deployer.src.models.workload_cancelled_exception import WorkloadCancelled
from clue_deployer.src.flushing_queue import FlushingQueue
from clue_deployer.src.workload_runner import WorkloadRunner
from clue_deployer.src.helm_wrapper import HelmWrapper
from clue_deployer.src.service.status_manager import StatusManager, StatusPhase
from os import path
import signal
import kubernetes
from kubernetes.client.rest import ApiException
from clue_deployer.src.logger import logger

class VariantRunner:

    def __init__(self, variant: Variant):
        self.variant = variant
        self.config = variant.config

    def run(self, results_path: str):
        variant = self.variant

        if len(variant.env.workload_settings) == 0:
            raise ValueError(f"Cant run {variant.name} with empty workload settings")
        # todo: autoscaling is set up upon branch deployment but cleaned up here

        node_file = path.join(
            results_path, f"measurements_node_{datetime.now().strftime('%d_%m_%Y_%H_%M')}.csv"
        )

        # noinspection PyProtectedMember
        node_channel = FlushingQueue(
            node_file, buffer_size=32, fields=NodeUsage._fields
        )

        pod_file = path.join(
            results_path, f"measurements_pod_{datetime.now().strftime('%d_%m_%Y_%H_%M')}.csv"
        )

        # noinspection PyProtectedMember
        pod_channel = FlushingQueue(
            pod_file, buffer_size=32, fields=PodUsage._fields
        )

        # tracker = ResourceTracker(exp.prometheus, observations_channel, tracker_namespaces, 10)
        tracker = ResourceTracker(
            prometheus_url=variant.prometheus,
            node_channel=node_channel,
            pod_channel=pod_channel,
            namespaces=[variant.namespace] + variant.infrastructure_namespaces,
            interval=10,
        )
        # Create a variant info
        with open(path.join(results_path, "variant_info.json"), "w") as f:
            f.write(variant.create_json())
        # Start resource tracker
        logger.info("Starting resource tracker")
        tracker.start()
        # MAIN timeout to kill the experiment after 2 min after the experiment should be over (to avoid hanging)
        timeout = variant.env.total_duration() + 2 * 60 + 30

        # noinspection PyUnusedLocal
        def cancel(sig=None, frame=None):
            """Handler for timeout, SIGINT, or manual cancellation."""
            if StatusManager.get() == StatusPhase.DONE:
                logger.info("Reached timout but experiment is already done, skipping cancellation.")
                return
            logger.warning(f"Workload timeout of {timeout}s reached, stopping the experiment.")
            tracker.stop()
            pod_channel.flush()
            node_channel.flush()
            if platform.system() != "Windows":
                signal.raise_signal(signal.SIGUSR1)  # raise SIGUSR1 on Unix-like systems
            else:
                raise WorkloadCancelled("Workload cancelled")  # raise custom exception on Windows
            StatusManager.set(StatusPhase.DONE, " workload timeout reached, Done :)")
            raise SystemExit(0)  # Exit gracefully

        # Set up SIGINT handler (Ctrl+C) for all platforms
        signal.signal(signal.SIGINT, cancel)

        # Set up SIGUSR1 handler for Unix-like systems
        if platform.system() != "Windows":
            signal.signal(signal.SIGUSR1, cancel)

        def set_timeout(seconds):
            """Cross-platform timeout setup."""
            if platform.system() != "Windows":
                # Unix-like systems: Use SIGALRM
                signal.signal(signal.SIGALRM, cancel)
                signal.alarm(seconds)
            else:
                # Windows: Use threading.Timer
                timer = threading.Timer(seconds, cancel)
                timer.start()
                return timer  # Return timer to allow cancellation
        try:
            logger.info(f"Variant started, deploying workload with timeout {timeout}s...")
            StatusManager.set(StatusPhase.IN_PROGRESS, "Starting workload with time out, variant deployment in progress...")
            # Set up the timeout
            timer = set_timeout(timeout)
            # Deploy workload on different node or locally and wait for workload to be completed (or timeout)
            workload_runner = WorkloadRunner(variant=variant)
            # Will run remotely or locally based on experiment
            try:
                workload_runner.run_workload(results_path)
            except WorkloadCancelled as e:
                logger.warning("Workload was cancelled due to exception: " + str(e))
            StatusManager.set(StatusPhase.DONE, " Expermint Done, flushing channels :)")
            logger.info("Finished running workload, stopping trackers and flushing channels")
            # stop resource tracker
            tracker.stop()
            node_channel.flush()
            pod_channel.flush()
        except SystemExit:
            _ = None  # Ignore SystemExit raised by the cancel function and clean up gracefully

        logger.info("Cleaning up timers after the experiment")
        # Clean up
        if platform.system() == "Windows" and timer:
            timer.cancel()  # Cancel the Windows timer
        elif platform.system() != "Windows":
            signal.alarm(0)  # Disable SIGALRM on Unix-like systems


    def cleanup(self, helm_wrapper: HelmWrapper):
        """
        Remove sets for autoscaling, remove workload pods,
        """
        logger.info("🧹 Cleaning up deployments...")

        if self.variant.autoscaling:
            hpas = kubernetes.client.AutoscalingV1Api()
            _hpas = hpas.list_namespaced_horizontal_pod_autoscaler(self.variant.namespace)
            for stateful_set in _hpas.items:
                hpas.delete_namespaced_horizontal_pod_autoscaler(name=stateful_set.metadata.name, namespace=self.variant.namespace)


        if self.variant.colocated_workload:
            core = kubernetes.client.CoreV1Api()
            # noinspection PyBroadException
            try:
                # Check if the pod exists before trying to delete it --> throws an error if it does not exist
                core.read_namespaced_pod(name="loadgenerator", namespace=self.variant.namespace)

                logger.info("Deleting loadgenerator pod")    
                core.delete_namespaced_pod(
                    name="loadgenerator", namespace=self.variant.namespace
                )
            except ApiException as e:
                if e.status == 404:
                    _ = None  # Pod does not exist, no action needed
                else:
                    logger.error(f"Error checking or deleting pod:" + str(e))
            except Exception as e:
                logger.error("Error cleaning up. Probably already deleted: " + str(e))
                pass
        
        helm_wrapper.uninstall()
