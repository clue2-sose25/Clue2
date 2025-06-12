from enum import Enum

class StatusPhase(str, Enum):
    PREPARING_CLUSTER = "Preparing the cluster"
    DEPLOYING_SUT = "Deploying SUT"
    WAITING = "Waiting"
    IN_PROGRESS = "In progress"
    DONE = "Done"
    FAILED = "Failed"