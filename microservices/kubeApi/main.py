from config import settings
import logging
import logging.config
from app import create_app

logging.config.dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)5s %(module)s.%(funcName)5s: %(message)s',
    }},
    'handlers': {'console': {
        'level': settings.log_level,
        'class': 'logging.StreamHandler',
        'stream': 'ext://sys.stdout',
        'formatter': 'default'
    }},
    'loggers': {
        'uvicorn': {
            'propagate': True
        },
        'fastapi': {
            'propagate': True
        }
    },
    'root': {
        'level': settings.log_level,
        'handlers': ['console']
    }
})

logger = logging.getLogger(__name__)

app = create_app()