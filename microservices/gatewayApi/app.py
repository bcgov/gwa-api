try:  # Python 3.5+
    from http import HTTPStatus as HTTPStatus
except ImportError:
    from http import client as HTTPStatus
import logging
import os
import time
import config
from werkzeug.exceptions import HTTPException
from authlib.jose.errors import JoseError, ExpiredTokenError
from flask import Flask, g, jsonify, request, make_response, url_for, Response
from flask_compress import Compress
from flask_cors import CORS
import threading

import v1.v1 as v1
import v2.v2 as v2


def set_cors_headers_on_response(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'X-Requested-With'
    response.headers['Access-Control-Allow-Methods'] = 'OPTIONS'
    return response

    

def create_app(test_config=None):

    log = logging.getLogger(__name__)


    # a = connexion.FlaskApp(__name__, specification_dir='v1/spec/')

    # a.add_api('v1.yaml', arguments={
    #     "tokeninfo_url": discovery["introspection_endpoint"],
    #     "authorization_url": discovery["authorization_endpoint"],
    #     "accesstoken_url": discovery["token_endpoint"]
    # })

    # app = a.app
    app = Flask(__name__)

    conf = config.Config()
    if test_config is None:
        app.config.update(conf.data)
    else:
        # load the test config if passed in
        app.config.update(conf.data)
        app.config.update(test_config)

    ##Routes##
    v1.Register(app)
    v2.Register(app)
    Compress(app)

    @app.before_request
    def before_request():
        from timeit import default_timer as timer

        g.request_start_time = timer()
        g.request_time = lambda: "%s" % (timer() - g.request_start_time)
        resp = Response()
        resp.headers['Content-Type'] = ["application/json"]

    @app.after_request
    def after_request(response):
        set_cors_headers_on_response(response)
        log.debug('Rendered in %ss', g.request_time())
        return response


    @app.errorhandler(HTTPStatus.NOT_FOUND)
    def not_found(param):
        content = jsonify({
            "error": "Not Found",
            "code": HTTPStatus.NOT_FOUND
        })
        return make_response(content, HTTPStatus.NOT_FOUND)


    @app.errorhandler(HTTPStatus.INTERNAL_SERVER_ERROR)
    def internal_server_error(error):
        log.error("Internal Error %s - %s" % (request.remote_addr, str(error)))
        content = jsonify({
            "error": "{error}",
            "code": HTTPStatus.INTERNAL_SERVER_ERROR
        })
        log.error(request.get_data())
        log.error(request.form)
        log.error(request.headers)
        return make_response(content, HTTPStatus.INTERNAL_SERVER_ERROR)

    @app.errorhandler(HTTPStatus.BAD_REQUEST)
    def bad_request_error(error):
        log.error("Bad Request %s - %s" % (request.remote_addr, str(error)))
        content = jsonify({
            "error": "Bad Request",
            "code": HTTPStatus.BAD_REQUEST
        })
        log.error(request.get_data())
        log.error(request.form)
        log.error(request.headers)
        return make_response(content, HTTPStatus.BAD_REQUEST)

    @app.errorhandler(HTTPException)
    def token_error(error):
        log.error("Denied access %s - %s" % (request.remote_addr, str(error)))
        content = jsonify({"error":"Invalid Token"})
        return make_response(content, HTTPStatus.UNAUTHORIZED)

    @app.errorhandler(JoseError)
    def forbidden(error):
        log.error("Denied access %s - %s" % (request.remote_addr, str(error)))
        content = jsonify({"error":"Invalid Token"})
        return make_response(content, HTTPStatus.UNAUTHORIZED)

    @app.errorhandler(ExpiredTokenError)
    def expired_token(error):
        content = jsonify({"error":"Token Expired"})
        return make_response(content, HTTPStatus.UNAUTHORIZED)

    @app.errorhandler(Exception)
    def other_exception(error):
        log.error("Unexpected error %s", type(error))
        log.exception(error)
        content = jsonify({"error":"Unexpected Error"})
        return make_response(content, HTTPStatus.BAD_REQUEST)

    @app.route('/', methods=['GET'], strict_slashes=False)
    def index():
        """
        Returns a list of valid API version endpoints
        :return: JSON of valid API version endpoints
        """
        return jsonify([url_for(".v1.get_status", _external=True)])
    

    @app.route('/version', methods=['GET'], strict_slashes=False)
    def version():
        """
        Get the current version of the api
        """
        from os import environ
        hash = ""
        if environ.get('GITHASH') is not None:
            hash = environ.get("GITHASH")

        # import pkg_resources  # part of setuptools
        # print(pkg_resources)
        # v = pkg_resources.get_distribution("gwa-kong").version
        v = ""
        
        version = v
        if hash != "":
            version += "-"+hash

        responseObj = {
            "v": v,
            "hash": hash,
            "version": version
        }
        return jsonify(responseObj)

    return app
