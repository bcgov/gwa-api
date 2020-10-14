import os
import logging
from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app

from v1.auth.auth import admin_jwt, enforce_authorization

graf = Blueprint('grafana', 'grafana')

# curl -v -H "Authorization: Bearer $TOK" https://grafana-qwzrwc-dev.pathfinder.gov.bc.ca/api/search
@graf.route('/dashboards',
           methods=['GET'], strict_slashes=False)
@admin_jwt(None)
def get_dashboard_list(namespace: str) -> object:
    return make_response(jsonify([]))

