import multiprocessing as mp
from typing import Tuple, Union
from clue_deployer.src.models.status_phase import StatusPhase

class StatusManager:
    """Manage deployment status across processes."""

    _status = None
    _lock = None

    @classmethod
    def init(cls, status_dict: Union[mp.Manager, None] = None, lock: Union[mp.Lock, None] = None) -> None:
        """Initialise the shared status dictionary and lock.
        If ``status_dict`` and ``lock`` are not provided a new ``multiprocessing.Manager``
        will be created. When using multiple processes the parent process should
        create the shared objects and pass them to ``init`` in each child.
        """
        if status_dict is not None and lock is not None:
            cls._status = status_dict
            cls._lock = lock
            return

        manager = mp.Manager()
        cls._status = manager.dict({
            "phase": StatusPhase.NO_DEPLOYMENT.value,
            "detail": "",
        })
        cls._lock = manager.Lock()

    @classmethod
    def _ensure_init(cls) -> None:
        if cls._status is None or cls._lock is None:
            cls.init()

    @classmethod
    def get(cls) -> Tuple[StatusPhase, str]:
        cls._ensure_init()
        with cls._lock:
            phase = StatusPhase(cls._status["phase"])
            detail = cls._status["detail"]
            return phase, detail

    @classmethod
    def set(cls, phase: StatusPhase, detail: str = "") -> None:
        cls._ensure_init()
        with cls._lock:
            cls._status["phase"] = phase.value
            cls._status["detail"] = detail