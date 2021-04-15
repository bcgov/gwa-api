#!/usr/bin/python
from gevent import monkey

# Patch Sockets to make requests asynchronous
monkey.patch_all()

import logging
import sys
import signal
from gevent.pywsgi import WSGIServer
# from server import app
from timeit import default_timer as timer
from app import create_app
import threading

import config
from logging.config import dictConfig

from swagger import setup_swagger_docs

conf = config.Config()

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '%(asctime)s %(levelname)5s %(module)-15s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': conf.data['logLevel'],
        'handlers': ['wsgi']
    }
})

log = logging.getLogger(__name__)

app = create_app()

threading.Thread(name='swagger docs', target=setup_swagger_docs, args=(app,["v1", "v2"])).start()

def signal_handler(sig, frame):
    log.info('You pressed Ctrl+C - exiting!')
    sys.exit(0)

def main(port: int = conf.data['apiPort']) -> object:
    """
    Run the Server
    :param port: Port number
    :return:
    """

    if sys.version_info[0] < 3:
        log.error('Server requires Python 3')
        return

    signal.signal(signal.SIGINT, signal_handler)

    log.info('Loading server...')
    load_start = timer()
    http = WSGIServer(('', port), app.wsgi_app, log=app.logger)
    load_end = timer()
    log.info('Load time: %s', str(load_end - load_start))

    log.info('Serving on port %s', str(port))
    http.serve_forever()
    log.info('Server terminated!')


if __name__ == '__main__':

    main()
