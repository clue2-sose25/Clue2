from multiprocessing import Queue
from clue_deployer.src.models.deploy_request import DeployRequest


class ExperimentQueue:
    def __init__(self, condition=None):
        self.condition = condition
        self.queue = Queue()
        self._mirror = []
        self._last_experiment = None

    @property
    def last_experiment(self):
        if self.last_experiment is None:
            raise ValueError("No experiment has been dequeued yet.")
        return self.last_experiment


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
        return self.queue.qsize()

    def flush(self):
        self.queue = Queue()
        self._mirror.clear()

    def __repr__(self):
        return f"<ExperimentQueue size={len(self._mirror)} contents={self._mirror}>"

    def get_all(self):
        return list(self._mirror)




    