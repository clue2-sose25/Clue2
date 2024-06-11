from datetime import datetime
from experiment import Experiment
from flushing_queue import FlushingQueue

from experiment_environment import ExperimentEnvironment
from experiment_autoscaling import ExperimentAutoscaling
from workload_runner import WorkloadRunner
from psc import ResourceTracker, NodeUsage
from os import path
import signal

import subprocess
import kubernetes


class ExperimentRunner:

    def __init__(self, experiment: Experiment):
        self.experiment = experiment

    def run(self, observations_out_path: str = "data/default"):

        exp = self.experiment
        # todo: autoscaling is set up upon branch deployment but cleaned up here

        datafile = path.join(
            observations_out_path, f"measurements_{datetime.now().strftime('%d_%m_%Y_%H_%M')}.csv"
        )
        # noinspection PyProtectedMember
        observations_channel = FlushingQueue(
            datafile, buffer_size=32, fields=NodeUsage._fields
        )
        tracker = ResourceTracker(exp.prometheus, observations_channel, exp.namespace, 10)

        with open(path.join(observations_out_path, "experiment.json"), "w") as f:
            f.write(exp.create_json())

        # 5. start workload
        # start resource tracker
        tracker.start()

        # noinspection PyUnusedLocal
        def cancel(sig, frame):
            tracker.stop()
            observations_channel.flush()
            signal.raise_signal(signal.SIGUSR1)  # raise signal to stop workload
            print("workload timeout reached.")

        signal.signal(signal.SIGALRM, cancel)

        # MAIN timeout to kill the experiment after 2 min after the workload should be completed
        # 8 stages + 2 minutes to deploy and cleanup
        timeout = ExperimentEnvironment().total_duration()
        print(f"starting workload with timeout {timeout}")
        signal.alarm(timeout)

        # deploy workload on different node or locally and wait for workload to be completed (or timeout)
        wlr = WorkloadRunner(experiment=exp)
        # will run remotely or locally based on experiment
        wlr.run_workload()

        # stop resource tracker
        tracker.stop()
        observations_channel.flush()
        signal.alarm(0)  # cancel alarm

    def cleanup(self):
        print("🧹 cleanup...")

        if self.experiment.autoscaling:
            ExperimentAutoscaling(self.experiment).cleanup_autoscaling()

        if self.experiment.colocated_workload:
            core = kubernetes.client.CoreV1Api()
            # noinspection PyBroadException
            try:
                core.delete_namespaced_pod(
                    name="loadgenerator", namespace=self.experiment.namespace
                )
            except Exception as e:
                print("error cleaning up, ignoring")
                print(e)
                pass

        subprocess.run(["helm", "uninstall", "teastore", "-n", self.experiment.namespace])
        subprocess.run(
            ["git", "checkout", "examples/helm/values.yaml"],
            cwd=path.join(self.experiment.env.teastore_path),
        )
        subprocess.run(
            ["git", "checkout", "tools/build_docker.sh"],
            cwd=path.join(self.experiment.env.teastore_path),
        )
