from flask import Blueprint, jsonify
from v2.routes.authz import authz
from v2.routes.gw_status import gw_status
from v2.routes.namespaces import ns
from v2.routes.whoami import whoami

from v3.routes.gateway import gw

v3 = Blueprint('v3', 'v3')

@v3.route('/status', methods=['GET'], strict_slashes=False)
def get_status():
    """
    Returns the overall API status
    :return: JSON of endpoint status
    """
    return jsonify({"status": "ok"})

class Register:
    def __init__(self, app):
        app.register_blueprint(v3, url_prefix="/v3")
        app.register_blueprint(authz, url_prefix="/v3/authz")
        app.register_blueprint(ns, url_prefix="/v3/namespaces")
        app.register_blueprint(gw, url_prefix="/v3/namespaces/<string:namespace>/gateway")
        app.register_blueprint(gw_status, url_prefix="/v3/namespaces/<string:namespace>/services")
        app.register_blueprint(whoami, url_prefix="/v3/whoami")
