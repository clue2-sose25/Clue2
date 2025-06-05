import logging
import sys
from pathlib import Path

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

# Create logger
logger = logging.getLogger("CLUE")
logger.setLevel(logging.INFO)

# Prevent propagation to root logger (this fixes the duplication)
logger.propagate = False

# Only add handlers if they don't already exist
if not logger.handlers:
    # Create formatters
    console_formatter = ColoredFormatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    log_file = "logs/app.log"
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)