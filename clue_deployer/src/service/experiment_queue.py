from queue import Queue
from threading import Condition
from typing import Optional
from clue_deployer.src.models.deploy_request import DeployRequest


class ExperimentQueue(Queue):
    """
    A thread-safe queue specifically designed for DeployRequest objects.
    The ExperimentRunner will handle conversion from DeployRequest to Experiment.
    """
    
    def __init__(self, condition: Optional[Condition] = None):
        super().__init__() 
        self.condition = condition or Condition()
        self._last_deploy_request: Optional[DeployRequest] = None

    @property
    def last_deploy_request(self) -> DeployRequest:
        """Get the last dequeued deploy request."""
        with self.mutex:
            if self._last_deploy_request is None:
                raise ValueError("No deploy request has been dequeued yet.")
            return self._last_deploy_request

    @last_deploy_request.setter
    def last_deploy_request(self, value: DeployRequest):
        """Set the last dequeued deploy request."""
        with self.mutex:
            self._last_deploy_request = value

    def enqueue(self, deploy_request: DeployRequest):
        """
        Enqueue a DeployRequest object.
        
        Args:
            deploy_request: The DeployRequest to add to the queue
            
        Raises:
            TypeError: If the item is not a DeployRequest
        """
        if not isinstance(deploy_request, DeployRequest):
            raise TypeError(f"Expected DeployRequest, got {type(deploy_request)}")
        
        with self.condition:
            self.put(deploy_request)
            self.condition.notify()

    def dequeue(self) -> DeployRequest:
        """
        Dequeue a deploy request from the queue.
        
        Returns:
            DeployRequest: The dequeued deploy request
            
        Raises:
            Empty: If the queue is empty
        """
        deploy_request = self.get()  
        if not isinstance(deploy_request, DeployRequest):
            raise TypeError(f"Expected DeployRequest object, got {type(deploy_request)}")
        
        self.last_deploy_request = deploy_request
        return deploy_request
    
    def dequeue_blocking(self) -> DeployRequest:
        """
        Dequeue a deploy request, blocking until one is available.
        
        Returns:
            DeployRequest: The dequeued deploy request
        """
        with self.condition:
            while self.empty():
                self.condition.wait()
            return self.dequeue()
    
    def get_item_at_index(self, index: int) -> DeployRequest:
        """Get an item at a specific index without removing it."""
        with self.mutex:
            if index < 0 or index >= len(self.queue):
                raise IndexError(f"Index {index} out of range for queue of size {len(self.queue)}")
            return self.queue[index]

    def remove_item_at_index(self, index: int) -> DeployRequest:
        """
        Remove and return an item at a specific index.
        
        Args:
            index: The index of the item to remove
            
        Returns:
            DeployRequest: The removed deploy request
            
        Raises:
            IndexError: If index is out of range
        """
        with self.mutex:
            if index < 0 or index >= len(self.queue):
                raise IndexError(f"Index {index} out of range for queue of size {len(self.queue)}")
            
            item = self.queue[index]
            del self.queue[index]
            
            # Only decrement unfinished_tasks if we actually removed something
            if self.unfinished_tasks > 0:
                self.unfinished_tasks -= 1
            
            # Notify waiting threads that space is available
            self.not_full.notify()
            return item

    def is_empty(self) -> bool:
        """Check if the queue is empty."""
        return self.empty()

    def size(self) -> int:
        """Get the current size of the queue."""
        with self.mutex:
            return len(self.queue)

    def flush(self):
        """Clear all items from the queue."""
        with self.mutex:
            self.queue.clear()
            self.unfinished_tasks = 0
            self.not_full.notify_all()
            # Also reset last_deploy_request since we've cleared everything
            self._last_deploy_request = None

    def get_all(self) -> list[DeployRequest]:
        """Get a copy of all items in the queue."""
        with self.mutex:
            return list(self.queue)

    def __repr__(self) -> str:
        """String representation of the queue."""
        with self.mutex:
            return f"<ExperimentQueue size={len(self.queue)} contents={list(self.queue)}>"

    def __len__(self) -> int:
        """Get the length of the queue."""
        return self.size()
    
    def peek(self) -> Optional[DeployRequest]:
        """Peek at the next item without removing it."""
        with self.mutex:
            if self.empty():
                return None
            return self.queue[0]