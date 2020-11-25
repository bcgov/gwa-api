import os
from flask import Blueprint, jsonify, request
from functools import reduce
from v1.routes.gateway import gw
from v1.routes.namespaces import ns
from v1.routes.serviceaccounts import sa
from v1.routes.whoami import whoami
from v1.routes.docs import docs
from v1.routes.gw_status import gw_status

v1 = Blueprint('v1', 'v1')

# @v1.route('oauth2-redirect.html', methods=['GET'], strict_slashes=False)
# def swagger_oauth2_redirect():
#     accessToken = request.args.get('access_token')

@v1.route('/status', methods=['GET'], strict_slashes=False)
def get_status():
    """
    Returns the overall API status
    :return: JSON of endpoint status
    """
    return jsonify({"status": "ok"})

class Register:
    def __init__(self, app):
        app.register_blueprint(v1, url_prefix="/v1")
        app.register_blueprint(gw_status, url_prefix="/v1/namespaces/<string:namespace>/services")
        app.register_blueprint(gw, url_prefix="/v1/namespaces/<string:namespace>/gateway")
        app.register_blueprint(sa, url_prefix="/v1/namespaces/<string:namespace>/serviceaccounts")
        app.register_blueprint(ns, url_prefix="/v1/namespaces")
        app.register_blueprint(whoami, url_prefix="/v1/whoami")
        app.register_blueprint(docs, url_prefix="/v1/api-docs")
