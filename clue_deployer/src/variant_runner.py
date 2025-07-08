import platform
import threading

from datetime import datetime
from clue_deployer.src.agent.psc.tracker import NodeUsage, PodUsage, ResourceTracker
from clue_deployer.src.configs.configs import CLUE_CONFIG, SUT_CONFIG
from clue_deployer.src.models.variant import Variant
from clue_deployer.src.models.workload import Workload
from clue_deployer.src.models.workload_cancelled_exception import WorkloadCancelled
from clue_deployer.src.flushing_queue import FlushingQueue
from clue_deployer.src.workload_runner import WorkloadRunner
from clue_deployer.src.helm_wrapper import HelmWrapper
from clue_deployer.src.service.status_manager import StatusManager, StatusPhase
from os import path
import signal
import kubernetes
from kubernetes.client.rest import ApiException
from clue_deployer.src.logger import process_logger as logger

class VariantRunner:

    def __init__(self, variant: Variant, workload: Workload):
        self.variant = variant
        self.workload = workload
        self._tracker = None
        self._node_channel = None
        self._pod_channel = None

    def _cancel_handler(self, sig=None, frame=None):
        """Handler for timeout, SIGINT, or manual cancellation."""
        if StatusManager.get() == StatusPhase.DONE:
            logger.info("Reached timeout but experiment is already done, skipping cancellation.")
            return
        
        logger.warning(f"Workload timeout of {CLUE_CONFIG.experiment_timeout}s reached, stopping the experiment.")
        
        if self._tracker:
            self._tracker.stop()
        if self._pod_channel:
            self._pod_channel.flush()
        if self._node_channel:
            self._node_channel.flush()
            
        if platform.system() != "Windows":
            signal.raise_signal(signal.SIGUSR1)  # raise SIGUSR1 on Unix-like systems
        else:
            raise WorkloadCancelled("Workload cancelled")  # raise custom exception on Windows
            
        StatusManager.set(StatusPhase.DONE, " workload timeout reached, Done :)")
        raise SystemExit(0)  # Exit gracefully

    def _setup_signal_handlers(self):
        """Set up signal handlers for cancellation."""
        # Set up SIGINT handler (Ctrl+C) for all platforms
        signal.signal(signal.SIGINT, self._cancel_handler)
        
        # Set up SIGUSR1 handler for Unix-like systems
        if platform.system() != "Windows":
            signal.signal(signal.SIGUSR1, self._cancel_handler)

    def _setup_timeout(self, seconds):
        """Cross-platform timeout setup."""
        if platform.system() != "Windows":
            # Unix-like systems: Use SIGALRM
            signal.signal(signal.SIGALRM, self._cancel_handler)
            signal.alarm(seconds)
            return None
        else:
            # Windows: Use threading.Timer
            timer = threading.Timer(seconds, self._cancel_handler)
            timer.start()
            return timer  # Return timer to allow cancellation

    def _cleanup_timeout(self, timer):
        """Clean up timeout mechanisms."""
        logger.info("Cleaning up timers after the experiment")
        if platform.system() == "Windows" and timer:
            timer.cancel()  # Cancel the Windows timer
        elif platform.system() != "Windows":
            signal.alarm(0)  # Disable SIGALRM on Unix-like systems

    def run(self, results_path: str):
        # TODO: autoscaling is set up upon branch deployment but cleaned up here
        node_file = path.join(
            results_path, f"measurements_node_{datetime.now().strftime('%d_%m_%Y_%H_%M')}.csv"
        )

        # noinspection PyProtectedMember
        self._node_channel = FlushingQueue(
            node_file, buffer_size=32, fields=NodeUsage._fields
        )

        pod_file = path.join(
            results_path, f"measurements_pod_{datetime.now().strftime('%d_%m_%Y_%H_%M')}.csv"
        )

        # noinspection PyProtectedMember
        self._pod_channel = FlushingQueue(
            pod_file, buffer_size=32, fields=PodUsage._fields
        )

        # tracker = ResourceTracker(exp.prometheus, observations_channel, tracker_namespaces, 10)
        self._tracker = ResourceTracker(
            prometheus_url=CLUE_CONFIG.prometheus_url,
            node_channel=self._node_channel,
            pod_channel=self._pod_channel,
            namespaces=[SUT_CONFIG.namespace] + SUT_CONFIG.infrastructure_namespaces,
            interval=10,
        )
        
        # Create a variant info
        with open(path.join(results_path, "variant_info.json"), "w") as f:
            f.write(self.variant.create_json())
        
        # Start resource tracker
        logger.info("Starting resource tracker")
        self._tracker.start()

        # Set up signal handlers
        self._setup_signal_handlers()

        try:
            logger.info(f"Variant started, deploying workload with timeout {CLUE_CONFIG.experiment_timeout}s...")
            StatusManager.set(StatusPhase.IN_PROGRESS, "Starting workload with time out, variant deployment in progress...")
            
            # Set up the timeout
            timer = self._setup_timeout(CLUE_CONFIG.experiment_timeout)
            
            # Deploy workload on different node or locally and wait for workload to be completed (or timeout)
            workload_runner = WorkloadRunner(self.variant, self.workload)
            
            # Will run remotely or locally based on experiment
            try:
                workload_runner.run_workload(results_path)
            except WorkloadCancelled as e:
                logger.warning("Workload was cancelled due to exception: " + str(e))
                
            StatusManager.set(StatusPhase.DONE, " Experiment Done, flushing channels :)")
            logger.info("Finished running workload, stopping trackers and flushing channels")
            
            # stop resource tracker
            self._tracker.stop()
            self._node_channel.flush()
            self._pod_channel.flush()
            
        except SystemExit:
            _ = None  # Ignore SystemExit raised by the cancel function and clean up gracefully
        finally:
            # Clean up timeout mechanisms
            self._cleanup_timeout(timer if 'timer' in locals() else None)

    def cleanup(self, helm_wrapper: HelmWrapper):
        """
        Remove sets for autoscaling, remove workload pods,
        """
        logger.info("🧹 Cleaning up deployments...")

        if self.variant.autoscaling:
            hpas = kubernetes.client.AutoscalingV1Api()
            _hpas = hpas.list_namespaced_horizontal_pod_autoscaler(SUT_CONFIG.namespace)
            for stateful_set in _hpas.items:
                hpas.delete_namespaced_horizontal_pod_autoscaler(name=stateful_set.metadata.name, namespace=SUT_CONFIG.namespace)

        if self.variant.colocated_workload:
            core = kubernetes.client.CoreV1Api()
            # noinspection PyBroadException
            try:
                # Check if the pod exists before trying to delete it --> throws an error if it does not exist
                core.read_namespaced_pod(name="loadgenerator", namespace=SUT_CONFIG.namespace)

                logger.info("Deleting loadgenerator pod")    
                core.delete_namespaced_pod(
                    name="loadgenerator", namespace=SUT_CONFIG.namespace
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