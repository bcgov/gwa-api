from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app

from v2.auth.auth import admin_jwt, uma_enforce
from clients.kong import get_tagged_resources_by_tag
from v2.services.namespaces import NamespaceService

gw_resources = Blueprint('gw_resources', 'gw_resources')

@gw_resources.route('',
           methods=['GET'], strict_slashes=False)
@admin_jwt(None)
@uma_enforce('namespace', 'GatewayConfig.Publish')
def get_resources(namespace: str) -> object:

    log = app.logger

    log.info("Get resources for %s" % namespace)

    # Optional query parameter for tag
    tag = "ns.%s" % namespace
    if request.args.get('tag'):
        tag = request.args.get('tag')
        # check that tag starts with ns.<namespace>
        if not tag.startswith("ns.%s." % namespace):
            abort(400, "Invalid tag parameter. Must start with ns.%s" % namespace)

    ns_svc = NamespaceService()
    ns_attributes = ns_svc.get_namespace_attributes(namespace)

    dp = get_data_plane(ns_attributes)
    kong_addr_override = app.config['data_planes'][dp].get("kong-addr")

    resources = get_tagged_resources_by_tag(tag, kong_addr_override)

    return make_response(jsonify(resources))

def get_data_plane(ns_attributes):
    default_data_plane = app.config['defaultDataPlane']
    return ns_attributes.get('perm-data-plane', [default_data_plane])[0]
