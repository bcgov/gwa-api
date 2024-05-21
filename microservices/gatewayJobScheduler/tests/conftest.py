import pytest
import logging
import logging.config

logging.config.dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)5s %(module)s.%(funcName)5s: %(message)s',
    }},
    'handlers': {'console': {
        'level': "DEBUG",
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
        'level': "DEBUG",
        'handlers': ['console']
    }
})
