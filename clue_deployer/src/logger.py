import logging
import sys
import multiprocessing as mp
import os


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


class SharedLogBuffer:
    def __init__(self, maxlen=1000):
        self.maxlen = maxlen
        # Try to initialize multiprocessing, but fall back gracefully
        try:
            # Only initialize multiprocessing if we're in the main process
            if (hasattr(os, 'getpid') and 
                mp.current_process().name == 'MainProcess' and
                hasattr(mp, 'Manager')):
                self.manager = mp.Manager()
                self.shared_list = self.manager.list()
                self.lock = self.manager.Lock()
                self.version = self.manager.Value('i', 0)  # shared int
                self.use_mp = True
            else:
                raise RuntimeError("Not in main process or mp not available")
        except (RuntimeError, AttributeError, OSError):
            # Fallback to thread-safe list if multiprocessing fails
            import threading
            self.shared_list = []
            self.lock = threading.Lock()
            self.manager = None
            self.version = 0  # simple int for thread-safe version
            self.use_mp = False

    def append(self, message):
        with self.lock:
            self.shared_list.append(message)
            while len(self.shared_list) > self.maxlen:
                self.shared_list.pop(0)

    def get_logs(self, n=None):
        with self.lock:
            logs = list(self.shared_list)
            return logs if n is None else logs[-n:]

    def clear(self):
        with self.lock:
            self.shared_list[:] = []
            if self.use_mp:
                self.version.value += 1  # increment version for mp
            else:
                self.version += 1  # increment version for threading

    def get_version(self):
        if self.use_mp:
            return self.version.value
        else:
            return self.version

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
# Use a lazy initialization approach to avoid multiprocessing issues
_logger = None
_shared_log_buffer = None

def get_logger():
    """Get the shared logger, initializing if necessary."""
    global _logger, _shared_log_buffer
    if _logger is None:
        try:
            _logger, _shared_log_buffer = setup_shared_logging()
        except Exception as e:
            # Fallback to simple logger if shared logging fails
            _logger = logging.getLogger("CLUE_FALLBACK")
            _logger.setLevel(logging.INFO)
            if not _logger.handlers:
                handler = logging.StreamHandler(sys.stdout)
                formatter = logging.Formatter(
                    '%(asctime)s [FALLBACK] [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                handler.setFormatter(formatter)
                _logger.addHandler(handler)
            _shared_log_buffer = None
    return _logger

def get_shared_log_buffer():
    """Get the shared log buffer, initializing if necessary."""
    global _logger, _shared_log_buffer
    if _shared_log_buffer is None and _logger is None:
        get_logger()  # This will initialize both
    return _shared_log_buffer

# For backward compatibility - but make these safe to import
try:
    logger = get_logger()
    shared_log_buffer = get_shared_log_buffer()
except Exception:
    # Ultimate fallback
    logger = logging.getLogger("CLUE_SAFE")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        logger.addHandler(handler)
    shared_log_buffer = None

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

class ProcessLogger:
    def __init__(self):
        self._logger = get_child_process_logger("MAIN", shared_log_buffer)

    @property
    def logger(self):
        return self._logger
    
    @logger.setter
    def logger(self, process_name):
        """Set the logger for a specific process."""
        if process_name is None:
            process_name = "NO_SUT"
        self._logger = get_child_process_logger(process_name, shared_log_buffer)
    
    def info(self, message, *args, **kwargs):
        """Log a message with the specified level."""
        self._logger.info(message, *args, **kwargs)
    
    def debug(self, message, *args, **kwargs):
        """Log a debug message."""
        self._logger.debug(message, *args, **kwargs)
    
    def warning(self, message, *args, **kwargs):
        """Log a warning message."""
        self._logger.warning(message, *args, **kwargs)
    
    def error(self, message, *args, **kwargs):
        """Log an error message."""
        self._logger.error(message, *args, **kwargs)
    


process_logger = ProcessLogger()