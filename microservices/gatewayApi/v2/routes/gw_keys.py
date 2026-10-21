from flask import Blueprint, jsonify, request, make_response, abort, current_app as app

from v2.auth.auth import admin_jwt, uma_enforce
from clients.kong import get_keys_and_key_sets
from v2.services.namespaces import NamespaceService

gw_keys = Blueprint('gw_keys', 'gw_keys')


@gw_keys.route('', methods=['GET'], strict_slashes=False)
@admin_jwt(None)
@uma_enforce('namespace', 'GatewayConfig.Publish')
def get_keys(namespace: str) -> object:
    log = app.logger
    log.info("Get keys for %s" % namespace)

    tag = "ns.%s" % namespace
    if request.args.get('tag'):
        tag = request.args.get('tag')
        if not tag.startswith("ns.%s." % namespace) and tag != ("ns.%s" % namespace):
            abort(400, "Invalid tag parameter. Must start with ns.%s" % namespace)

    key_set = request.args.get('key_set') or request.args.get('keySet')

    ns_svc = NamespaceService()
    ns_attributes = ns_svc.get_namespace_attributes(namespace)

    dp = get_data_plane(ns_attributes)
    kong_addr_override = app.config['data_planes'][dp].get("kong-addr")

    payload = get_keys_and_key_sets(tag, key_set, kong_addr_override)
    return make_response(jsonify(payload))


def get_data_plane(ns_attributes):
    default_data_plane = app.config['defaultDataPlane']
    return ns_attributes.get('perm-data-plane', [default_data_plane])[0]
