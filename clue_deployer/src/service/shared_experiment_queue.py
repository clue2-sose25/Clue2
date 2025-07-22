from multiprocessing import Manager
from multiprocessing.managers import SyncManager
from typing import List
from clue_deployer.src.models.deploy_request import DeployRequest

class SharedExperimentQueue:
    def __init__(self, manager: SyncManager):
        self.items = manager.list()  # Shared list
        self.lock = manager.Lock()   # Shared lock
        self.condition = manager.Condition(self.lock)  # Condition using the same lock
        self._last_deploy_request = None

    def enqueue(self, deploy_request: DeployRequest):
        if not isinstance(deploy_request, DeployRequest):
            raise TypeError(f"Expected DeployRequest, got {type(deploy_request)}")
        with self.lock:
            self.items.append(deploy_request)
            self.condition.notify()

    def dequeue(self) -> DeployRequest:
        with self.lock:
            if not self.items:
                raise ValueError("Queue is empty")
            deploy_request = self.items.pop(0)
            self._last_deploy_request = deploy_request
            return deploy_request

    def dequeue_blocking(self) -> DeployRequest:
        with self.condition:
            while not self.items:
                self.condition.wait()
            return self.dequeue()

    def get_all(self) -> List[DeployRequest]:
        with self.lock:
            return list(self.items)

    def size(self) -> int:
        with self.lock:
            return len(self.items)

    def is_empty(self) -> bool:
        with self.lock:
            return len(self.items) == 0

    def remove_item_at_index(self, index: int) -> DeployRequest:
        with self.lock:
            if index < 0 or index >= len(self.items):
                raise IndexError(f"Index {index} out of range")
            return self.items.pop(index)

    def flush(self):
        with self.lock:
            self.items[:] = []
            self._last_deploy_request = None