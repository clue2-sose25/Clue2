import logging
import logging.config
from pathlib import Path

def setup_logging(log_level=logging.INFO, log_file=None):
    """
    Setup logging configuration for the entire application
    """
    # Create logs directory if it doesn't exist
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Define logging configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            }
        },
        'root': {
            'level': log_level,
            'handlers': ['console']
        }
    }
    
    # Add file handler if log_file is specified
    if log_file:
        config['handlers']['file'] = {
            'class': 'logging.FileHandler',
            'level': log_level,
            'formatter': 'detailed',
            'filename': log_file,
            'mode': 'a'
        }
        config['root']['handlers'].append('file')
    
    # Apply configuration
    logging.config.dictConfig(config)