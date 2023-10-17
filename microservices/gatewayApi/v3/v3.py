from flask import Blueprint, jsonify
from v3.routes.gateway import gw
from v3.routes.gw_status import gw_status
from v3.routes.whoami import whoami

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
        app.register_blueprint(gw, url_prefix="/v3/namespaces/<string:namespace>/gateway")
        app.register_blueprint(gw_status, url_prefix="/v3/namespaces/<string:namespace>/services")
        app.register_blueprint(whoami, url_prefix="/v3/whoami")
