import os
from flask import Blueprint, jsonify, request
from functools import reduce
from v2.routes.authz import authz
from v2.routes.gateway import gw
from v2.routes.gw_status import gw_status
from v2.routes.namespaces import ns
from v2.routes.migrate_v1 import mg
from v2.routes.whoami import whoami
from v2.routes.consumers import consumers

v2 = Blueprint('v2', 'v2')

@v2.route('/status', methods=['GET'], strict_slashes=False)
def get_status():
    """
    Returns the overall API status
    :return: JSON of endpoint status
    """
    return jsonify({"status": "ok"})

class Register:
    def __init__(self, app):
        app.register_blueprint(v2, url_prefix="/v2")
        app.register_blueprint(authz, url_prefix="/v2/authz")
        app.register_blueprint(ns, url_prefix="/v2/namespaces")
        app.register_blueprint(gw, url_prefix="/v2/namespaces/<string:namespace>/gateway")
        app.register_blueprint(gw_status, url_prefix="/v2/namespaces/<string:namespace>/services")
        app.register_blueprint(whoami, url_prefix="/v2/whoami")
        app.register_blueprint(mg, url_prefix="/v2/migration")
        app.register_blueprint(consumers, url_prefix="/v2/namespaces/<string:namespace>/consumers")
