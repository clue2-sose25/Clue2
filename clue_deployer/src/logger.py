import logging
import sys
import multiprocessing as mp


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
        self.manager = mp.Manager()
        self.shared_list = self.manager.list()
        self.maxlen = maxlen
        self.lock = self.manager.Lock()
        self.version = self.manager.Value('i', 0)  # shared int

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
            self.version.value += 1  # increment version

    def get_version(self):
        return self.version.value

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
    
    def info(self, message):
        """Log a message with the specified level."""
        self._logger.info(message)
    
    def debug(self, message):
        """Log a debug message."""
        self._logger.debug(message)
    
    def warning(self, message):
        """Log a warning message."""
        self._logger.warning(message)
    
    def error(self, message):
        """Log an error message."""
        self._logger.error(message)
    


process_logger = ProcessLogger()