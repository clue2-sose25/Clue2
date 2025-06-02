import threadingAdd commentMore actions
from typing import Tuple
from .status import Phase

class StatusManager:
    _lock   = threading.Lock()
    _phase  = Phase.PREPARING_CLUSTER
    _detail = ""                   # optionale Zusatzinfo (→ UI)

    @classmethod
    def get(cls) -> Tuple[Phase, str]:
        with cls._lock:
            return cls._phase, cls._detail

    @classmethod
    def set(cls, phase: Phase, detail: str = "") -> None:
        with cls._lock:
            cls._phase, cls._detail = phase, detail
