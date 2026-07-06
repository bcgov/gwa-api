from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app

from v2.auth.auth import admin_jwt, uma_enforce
from clients.kong import get_tagged_resources_by_ns

gw_resources = Blueprint('gw_resources', 'gw_resources')

@gw_resources.route('',
           methods=['GET'], strict_slashes=False)
@admin_jwt(None)
@uma_enforce('namespace', 'GatewayConfig.Publish')
def get_resources(namespace: str) -> object:

    log = app.logger

    log.info("Get resources for %s" % namespace)

    resources = get_tagged_resources_by_ns(namespace)

    return make_response(jsonify(resources))
