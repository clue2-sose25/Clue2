from multiprocessing import Manager
from clue_deployer.src.models.status_phase import StatusPhase

class SharedStatusManager:
    def __init__(self, shared_dict):
        self._shared_dict = shared_dict

    def set(self, phase: StatusPhase, detail: str = ""):
        self._shared_dict["phase"] = phase
        self._shared_dict["detail"] = detail

    def get(self):
        return self._shared_dict["phase"], self._shared_dict["detail"]

