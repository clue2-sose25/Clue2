from multiprocessing import Manager, Condition
from queue import Queue
from clue_deployer.src.models.deploy_request import DeployRequest

class ExperimentQueue:
    def __init__(self, condition=None):
        self.condition = condition
        manager = Manager()  # Create a manager for shared objects
        self.queue = Queue()  # Regular queue for thread-safe operations
        self._mirror = manager.list()  # Shared list for cross-process updates
        self._last_experiment = None

    @property
    def last_experiment(self):
        if self._last_experiment is None:
            raise ValueError("No experiment has been dequeued yet.")
        return self._last_experiment

    @last_experiment.setter
    def last_experiment(self, value):
        self._last_experiment = value

    def enqueue(self, experiment: DeployRequest):
        with self.condition:
            self.queue.put(experiment)
            self._mirror.append(experiment)  
            self.condition.notify()  # Notify the worker that a new item is available

    def dequeue(self):
        experiment = self.queue.get()
        if experiment in self._mirror:
            self._mirror.remove(experiment)  
        self.last_experiment = experiment
        return experiment

    def is_empty(self):
        return self.queue.empty()

    def size(self):
        return self._mirror.__len__()

    def flush(self):
        self.queue = Queue()
        self._mirror.clear()

    def __repr__(self):
        return f"<ExperimentQueue size={len(self._mirror)} contents={list(self._mirror)}>"

    def get_all(self):
        return list(self._mirror)  # Return a copy of the shared mirror