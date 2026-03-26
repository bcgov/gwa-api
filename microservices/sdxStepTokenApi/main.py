from config import settings
import logging.config

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.json.JsonFormatter',
            'format': '%(levelname)s %(name)s %(funcName)s %(message)s',
            'timestamp': True,  # Adds ISO-8601 timestamp field
            'reserved_attrs': [  # Exclude uvicorn's color_message field
                'color_message', 'args', 'created', 'exc_info', 'exc_text',
                'filename', 'levelno', 'lineno', 'module', 'msecs', 'msg',
                'pathname', 'process', 'processName', 'relativeCreated',
                'stack_info', 'thread', 'threadName', 'taskName'
            ],
        },
    },
    'handlers': {
        'console': {
            'level': settings.log_level,
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
            'formatter': 'json',
        },
    },
    'loggers': {
        'uvicorn': {
            'propagate': True,
        },
        'fastapi': {
            'propagate': True,
        },
    },
    'root': {
        'level': settings.log_level,
        'handlers': ['console'],
    },
})

from app import create_app

logger = logging.getLogger(__name__)

app = create_app()
