from config import settings
import logging.config

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.json.JsonFormatter',
            'format': '%(asctime)s %(levelname)s %(name)s %(funcName)s %(message)s',
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
