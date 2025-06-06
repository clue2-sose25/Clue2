from abc import ABC, abstractmethod
from clue_deployer.src.experiment_environment import ExperimentEnvironment
from enum import StrEnum


LOADGENERATOR_DURATION = 64 # 600
LOADGENERATOR_MAX_DAILY_USERS = 100 # 1000

class WorkloadType(StrEnum):
    SHAPED = "shaped"
    RAMPUP = "rampup"
    PAUSING = "pausing"
    FIXED = "fixed"

def get_workload_instance(workload_type: WorkloadType) -> "Workload":
    """
    Returns an instance of the corresponding workload class for the given workload type.
    """
    workload_mapping = {
        WorkloadType.SHAPED: ShapedWorkload,
        WorkloadType.RAMPUP: RampingWorkload,
        WorkloadType.PAUSING: PausingWorkload,
        WorkloadType.FIXED: FixedRampingWorkload,
    }
    workload_class = workload_mapping[workload_type]
    return workload_class()  # Instantiate the class
class Workload(ABC):
    """
    Abstract base class for all workloads. Contains shared constants and enforces a common interface.
    """
    def __init__(self, load_generator_duration: int = LOADGENERATOR_DURATION, max_daily_users: int = LOADGENERATOR_MAX_DAILY_USERS):
        self._load_generator_duration = load_generator_duration
        self._max_daily_users = max_daily_users

    @property
    def load_generator_duration(self) -> int:
        """
        Read-only property for load generator duration.
        """
        return self._load_generator_duration

    @property
    def max_daily_users(self) -> int:
        """
        Read-only property for maximum daily users.
        """
        return self._max_daily_users

    @abstractmethod
    def set_workload(self, exp: ExperimentEnvironment) -> None:
        """
        Abstract method to set workload settings for an experiment.
        Must be implemented by subclasses.
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(load_generator_duration={self.load_generator_duration}, max_daily_users={self.max_daily_users})"


class ShapedWorkload(Workload):
    """
    Workload with custom load shape behavior.
    """
    def set_workload(self, exp: ExperimentEnvironment) -> None:
        exp.workload_settings = {
            "LOADGENERATOR_STAGE_DURATION": self.load_generator_duration // 8,  # runtime per load stage in seconds
            "LOADGENERATOR_MAX_DAILY_USERS": self.max_daily_users,  # max daily users
            "LOCUST_LOCUSTFILE": "./consumerbehavior.py,./loadshapes.py",  # 8 different stages
        }
        exp.tags.append(WorkloadType.SHAPED)
        exp.timeout_duration = self.load_generator_duration + 60


class RampingWorkload(Workload):
    """
    Workload that ramps up users at a constant rate.
    """
    def set_workload(self, exp: ExperimentEnvironment) -> None:
        exp.workload_settings = {
            "LOCUST_LOCUSTFILE": "./locustfile.py",
            "LOCUST_RUN_TIME": f'{self.load_generator_duration}s',
            "LOCUST_SPAWN_RATE": 3,  # users per second
            "LOCUST_USERS": self.max_daily_users,
        }
        exp.tags.append(WorkloadType.RAMPUP)
        exp.timeout_duration = self.load_generator_duration + 60
    
class PausingWorkload(Workload):
    """
    Workload that starts 20 pausing users, no ramp-up for the duration.
    """
    def set_workload(self, exp: ExperimentEnvironment) -> None:
        exp.workload_settings = {
            "LOCUST_LOCUSTFILE": "./pausing_users.py",
            "LOCUST_RUN_TIME": f'{self.load_generator_duration}s',
            "LOCUST_SPAWN_RATE": 1,
            "LOCUST_USERS": 10,
            "PAUSE_BACKOFF": 120,
        }
        exp.timeout_duration = self.load_generator_duration + 60
        exp.tags.append(WorkloadType.PAUSING)


class FixedRampingWorkload(Workload):
    """
    Workload that ramps up to max users for at most 1000 requests (failed or successful),
    running for at most the specified duration.
    """
    def set_workload(self, exp: ExperimentEnvironment) -> None:
        exp.workload_settings = {
            "LOCUST_LOCUSTFILE": "./fixed_requests.py",
            "LOCUST_RUN_TIME": f'{self.load_generator_duration}s',
            "LOCUST_SPAWN_RATE": 1,
            "LOCUST_USERS": self.max_daily_users,
            "MAXIMUM_REQUESTS": 200,
        }
        exp.tags.append(WorkloadType.FIXED)
        exp.timeout_duration = self.load_generator_duration + 60