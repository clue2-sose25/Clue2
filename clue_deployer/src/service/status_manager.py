import threading
from typing import Tuple
from clue_deployer.src.models.status_phase import StatusPhase

class StatusManager:
    _lock   = threading.Lock()
    _phase  = StatusPhase.PREPARING_CLUSTER
    _detail = ""

    @classmethod
    def get(cls) -> Tuple[StatusPhase, str]:
        with cls._lock:
            return cls._phase, cls._detail

    @classmethod
    def set(cls, phase: StatusPhase, detail: str = "") -> None:
        with cls._lock:
            cls._phase, cls._detail = phase, detail
