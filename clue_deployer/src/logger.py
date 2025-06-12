import logging
import sys
import threading
import multiprocessing as mp
from pathlib import Path
from collections import deque
from queue import Queue, Empty
import time

# Define ANSI color codes
COLORS = {
    'DEBUG': '\033[94m',   # Blue
    'INFO': '\033[92m',    # Green
    'WARNING': '\033[93m', # Yellow
    'ERROR': '\033[91m',   # Red
    'CRITICAL': '\033[95m' # Magenta
}
RESET = '\033[0m'

# Custom formatter for colored console output
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        formatted = super().format(record)
        levelname = record.levelname
        if levelname in COLORS:
            return f"{COLORS[levelname]}{formatted}{RESET}"
        return formatted

# Thread-safe log buffer using a queue and background thread
class ThreadSafeLogBuffer:
    def __init__(self, maxlen=1000):
        self.maxlen = maxlen
        self.buffer = deque(maxlen=maxlen)
        self.queue = Queue()
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.worker_thread = None
        self._start_worker()
    
    def _start_worker(self):
        """Start the background worker thread to process log messages."""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
    
    def _worker(self):
        """Background worker that processes messages from the queue."""
        while not self.stop_event.is_set():
            try:
                # Get message from queue with timeout
                message = self.queue.get(timeout=0.1)
                with self.lock:
                    self.buffer.append(message)
                self.queue.task_done()
            except Empty:
                continue
            except Exception as e:
                # Handle any unexpected errors in the worker thread
                print(f"Error in log buffer worker: {e}", file=sys.stderr)
    
    def append(self, message):
        """Thread-safe append to buffer."""
        try:
            self.queue.put(message, block=False)
        except:
            # If queue is full, we'll just drop the message
            pass
    
    def get_logs(self, n=None):
        """Get logs from buffer in a thread-safe manner."""
        with self.lock:
            if n is None:
                return list(self.buffer)
            else:
                return list(self.buffer)[-n:] if len(self.buffer) >= n else list(self.buffer)
    
    def clear(self):
        """Clear the buffer in a thread-safe manner."""
        with self.lock:
            self.buffer.clear()
    
    def stop(self):
        """Stop the worker thread."""
        self.stop_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)

# Global log buffer instance
LEN_LOG_BUFFER=1000
LOG_BUFFER = ThreadSafeLogBuffer(maxlen=LEN_LOG_BUFFER)

# Custom handler for the thread-safe buffer
class ThreadSafeBufferHandler(logging.Handler):
    def __init__(self, buffer):
        super().__init__()
        self.buffer = buffer

    def emit(self, record):
        try:
            msg = self.format(record)
            self.buffer.append(msg)
        except Exception:
            self.handleError(record)

# Multiprocessing-aware logger setup
class MultiprocessingLoggerSetup:
    _initialized = False
    _lock = threading.Lock()
    
    @classmethod
    def setup_logger(cls, process_name=None):
        """Setup logger for multiprocessing environment."""
        with cls._lock:
            logger_name = f"CLUE_{process_name}" if process_name else "CLUE"
            logger = logging.getLogger(logger_name)
            
            # Only setup if not already initialized for this process
            if not getattr(logger, '_mp_initialized', False):
                logger.setLevel(logging.INFO)
                logger.propagate = False
                
                # Clear any existing handlers
                logger.handlers.clear()
                
                # Create formatters
                console_formatter = ColoredFormatter(
                    f'%(asctime)s [{process_name or "MAIN"}] [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                
                # Console handler
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(logging.INFO)
                console_handler.setFormatter(console_formatter)
                logger.addHandler(console_handler)
                
                # Buffer handler (only for main process)
                if process_name is None:  # Main process
                    buffer_handler = ThreadSafeBufferHandler(LOG_BUFFER)
                    buffer_handler.setLevel(logging.INFO)
                    buffer_handler.setFormatter(logging.Formatter(
                        '%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S'
                    ))
                    logger.addHandler(buffer_handler)
                
                logger._mp_initialized = True
                
            return logger

# Initialize the main logger
logger = MultiprocessingLoggerSetup.setup_logger()

# Alternative approach using multiprocessing Manager for shared log buffer
class SharedLogBuffer:
    def __init__(self, maxlen=1000):
        self.manager = mp.Manager()
        self.shared_list = self.manager.list()
        self.maxlen = maxlen
        self.lock = self.manager.Lock()
    
    def append(self, message):
        """Thread and process-safe append."""
        with self.lock:
            self.shared_list.append(message)
            # Maintain maxlen
            while len(self.shared_list) > self.maxlen:
                self.shared_list.pop(0)
    
    def get_logs(self, n=None):
        """Get logs in a thread and process-safe manner."""
        with self.lock:
            logs = list(self.shared_list)
            if n is None:
                return logs
            else:
                return logs[-n:] if len(logs) >= n else logs
    
    def clear(self):
        """Clear the buffer."""
        with self.lock:
            self.shared_list[:] = []

# Shared buffer handler for multiprocessing
class SharedBufferHandler(logging.Handler):
    def __init__(self, shared_buffer):
        super().__init__()
        self.shared_buffer = shared_buffer

    def emit(self, record):
        try:
            msg = self.format(record)
            self.shared_buffer.append(msg)
        except Exception:
            self.handleError(record)

# Function to setup shared logging for multiprocessing
def setup_shared_logging():
    """Setup shared logging buffer for multiprocessing."""
    shared_buffer = SharedLogBuffer(maxlen=1000)
    
    # Setup main process logger
    main_logger = logging.getLogger("CLUE_MAIN")
    main_logger.setLevel(logging.INFO)
    main_logger.propagate = False
    
    if not main_logger.handlers:
        # Console handler
        console_formatter = ColoredFormatter(
            '%(asctime)s [MAIN] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        main_logger.addHandler(console_handler)
        
        # Shared buffer handler
        buffer_handler = SharedBufferHandler(shared_buffer)
        buffer_handler.setLevel(logging.INFO)
        buffer_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        main_logger.addHandler(buffer_handler)
    
    return main_logger, shared_buffer

# Initialize shared logging at module level for easy importing
logger, shared_log_buffer = setup_shared_logging()

# Utility function to get logger for child processes
def get_child_process_logger(process_name, shared_buffer=None):
    """Get a logger configured for a child process."""
    logger_name = f"CLUE_{process_name}"
    child_logger = logging.getLogger(logger_name)
    child_logger.setLevel(logging.INFO)
    child_logger.propagate = False
    
    if not child_logger.handlers:
        # Console handler with process name
        console_formatter = ColoredFormatter(
            f'%(asctime)s [{process_name}] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        child_logger.addHandler(console_handler)
        
        # Add shared buffer handler if provided
        if shared_buffer:
            buffer_handler = SharedBufferHandler(shared_buffer)
            buffer_handler.setLevel(logging.INFO)
            buffer_handler.setFormatter(logging.Formatter(
                f'%(asctime)s [{process_name}] [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            child_logger.addHandler(buffer_handler)
    
    return child_logger