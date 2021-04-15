import os
from flask import Blueprint, jsonify, request
from functools import reduce
from v2.routes.authz import authz

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
