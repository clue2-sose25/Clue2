from multiprocessing import Manager, Condition
from clue_deployer.src.models.deploy_request import DeployRequest
from queue import Queue


class ExperimentQueue(Queue):
    def __init__(self, condition=None):
        super().__init__() 
        self.condition = condition
        manager = Manager()  # Create a manager for shared objects
        self._last_experiment = None

    @property
    def last_experiment(self):
        if self._last_experiment is None:
            raise ValueError("No experiment has been dequeued yet.")
        return self._last_experiment

    @last_experiment.setter
    def last_experiment(self, value):
        with self.mutex:
            self._last_experiment = value

    def enqueue(self, experiment: DeployRequest):
        with self.condition:
            self.put(experiment)
            self.condition.notify()  # Notify the worker that a new item is available

    def dequeue(self):
        experiment = self.get()  
        self.last_experiment = experiment
        return experiment
    
    def get_item_at_index(self, index):
        with self.mutex:
            return self.queue[index]

    def remove_item_at_index(self, index):
        with self.mutex:
            item = self.queue[index]
            del self.queue[index]
            self.unfinished_tasks -= 1
            self.not_full.notify()
            return item

    def is_empty(self):
        return self.empty()

    def size(self):
        return len(self.queue)

    def flush(self):
        with self.mutex:
            self.queue.clear()        # Clear the underlying deque
            self.unfinished_tasks = 0 # Reset unfinished tasks
            self.not_full.notify_all()  # Notify any waiting threads

    def __repr__(self):
        return f"<ExperimentQueue size={len(self._mirror)} contents={list(self._mirror)}>"

    def get_all(self):
        return list(self.queue)  # Return a copy of the shared mirror