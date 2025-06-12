import multiprocessing as mp
from typing import Tuple
from clue_deployer.src.models.status_phase import StatusPhase

class StatusManager:
    _manager = mp.Manager()
    _lock = _manager.Lock()
    _status = _manager.dict({
        "phase": StatusPhase.PREPARING_CLUSTER.value,
        "detail": "",
    })

    @classmethod
    def get(cls) -> Tuple[StatusPhase, str]:
        with cls._lock:
            phase = StatusPhase(cls._status["phase"])
            detail = cls._status["detail"]
            return phase, detail

    @classmethod
    def set(cls, phase: StatusPhase, detail: str = "") -> None:
        with cls._lock:
            cls._status["phase"] = phase.value
            cls._status["detail"] = detail
