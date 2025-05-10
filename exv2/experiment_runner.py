import platform
import threading
from datetime import datetime

from psc.tracker import PodUsage

from experiment import Experiment
from workload_cancelled_exception import WorkloadCancelled
from flushing_queue import FlushingQueue
from workload_runner import WorkloadRunner
from psc import ResourceTracker, NodeUsage
from os import path
import signal
import subprocess
import kubernetes
import logging

class ExperimentRunner:

    def __init__(self, experiment: Experiment):
        self.experiment = experiment

    def run(self, observations_out_path: str = "data/default"):
        exp = self.experiment

        if len(exp.env.workload_settings) == 0:
            raise ValueError(f"cant run {exp.name} with empty workload settings")
        # todo: autoscaling is set up upon branch deployment but cleaned up here

        node_file = path.join(
            observations_out_path, f"measurements_node_{datetime.now().strftime('%d_%m_%Y_%H_%M')}.csv"
        )

        # noinspection PyProtectedMember
        node_channel = FlushingQueue(
            node_file, buffer_size=32, fields=NodeUsage._fields
        )

        pod_file = path.join(
            observations_out_path, f"measurements_pod_{datetime.now().strftime('%d_%m_%Y_%H_%M')}.csv"
        )

        # noinspection PyProtectedMember
        pod_channel = FlushingQueue(
            pod_file, buffer_size=32, fields=PodUsage._fields
        )

        # tracker = ResourceTracker(exp.prometheus, observations_channel, tracker_namespaces, 10)
        tracker = ResourceTracker(
            prometheus_url=exp.prometheus,
            node_channel=node_channel,
            pod_channel=pod_channel,
            namespaces=[exp.namespace] + exp.infrastructure_namespaces,
            interval=10,
        )

        with open(path.join(observations_out_path, "experiment.json"), "w") as f:
            f.write(exp.create_json())

        # 5. start workload
        # start resource tracker
        logging.debug("starting tracker")
        tracker.start()

        # MAIN timeout to kill the experiment after 2 min after the experiment should be over (to avoid hanging)
        timeout = exp.env.total_duration() + 2 * 60 + 30

        # noinspection PyUnusedLocal
        def cancel(sig=None, frame=None):
            """Handler for timeout, SIGINT, or manual cancellation."""
            tracker.stop()
            pod_channel.flush()
            node_channel.flush()
            if platform.system() != "Windows":
                signal.raise_signal(signal.SIGUSR1)  # raise SIGUSR1 on Unix-like systems
            else:
                raise WorkloadCancelled("Workload cancelled")  # raise custom exception on Windows
            logging.warning(f"workload timeout ({timeout})s reached.")
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

        # Example usage
        try:
            logging.info(f"starting workload with timeout {timeout}")
            # Set up the timeout
            timer = set_timeout(timeout)

            # deploy workload on different node or locally and wait for workload to be completed (or timeout)
            wlr = WorkloadRunner(experiment=exp)
            # will run remotely or locally based on experiment
            try:
                wlr.run_workload(observations_out_path)
            except WorkloadCancelled:
                logging.info("Workload stopped due to cancellation")

            logging.info("finished running workload, stopping trackers and flushing channels")
            # stop resource tracker
            tracker.stop()
            node_channel.flush()
            pod_channel.flush()

        except SystemExit:
            # Clean up
            if platform.system() == "Windows" and timer:
                timer.cancel()  # Cancel the Windows timer
            elif platform.system() != "Windows":
                signal.alarm(0)  # Disable SIGALRM on Unix-like systems
            logging.info("Program terminated")


    def cleanup(self):
        """
        Remove sets for autoscaling, remove workload pods,
        """
        print("🧹 Cleaning up...")

        if self.experiment.autoscaling:
            hpas = kubernetes.client.AutoscalingV1Api()
            _hpas = hpas.list_namespaced_horizontal_pod_autoscaler(self.experiment.namespace)
            for stateful_set in _hpas.items:
                hpas.delete_namespaced_horizontal_pod_autoscaler(name=stateful_set.metadata.name, namespace=self.experiment.namespace)


        if self.experiment.colocated_workload:
            core = kubernetes.client.CoreV1Api()
            # noinspection PyBroadException
            try:
                core.delete_namespaced_pod(
                    name="loadgenerator", namespace=self.experiment.namespace
                )
            except Exception as e:
                logging.error("Error cleaning up. Probably already deleted: " + str(e))
                pass

        subprocess.run(["helm", "uninstall", "teastore", "-n", self.experiment.namespace])
        subprocess.run(
            ["git", "checkout", "examples/helm/values.yaml"],
            cwd=path.join(self.experiment.env.sut_path),
        )
        subprocess.run(
            ["git", "checkout", "tools/build_docker.sh"],
            cwd=path.join(self.experiment.env.sut_path),
        )
