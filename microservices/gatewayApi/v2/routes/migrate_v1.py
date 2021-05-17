# This service provides a way to migrate
# the data from V1 to V2.
# 
# This involves:
# * exporting namespaces, service accounts, and users list

from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app

from v2.auth.auth import admin_jwt, uma_enforce

from keycloak.exceptions import raise_error_from_response, KeycloakGetError
from keycloak.urls_patterns import URL_ADMIN_CLIENTS
from subprocess import Popen, PIPE, STDOUT
from utils.clientid import client_id_valid, generate_client_id
from clients.keycloak import admin_api
from clients.kong import get_plugins, get_services_by_ns, get_routes_by_ns

mg = Blueprint('migration.v2', 'migration')

@mg.route('export',
           methods=['GET'], strict_slashes=False)
@admin_jwt('Namespace.Admin')
def export_details() -> object:
    keycloak_admin = admin_api()

    response = []
    all_plugins = get_plugins()
    acl_namespaces = get_acl_namespaces(keycloak_admin)
    namespaces = get_namespaces(keycloak_admin)
    for namespace in namespaces:
        ns_name = namespace['name']
        ns_id = namespace['id']
        ns = {
            "namespace": ns_name,
            "attributes": {},
            "view_membership": [],
            "admin_membership": [],
            "service_accounts": [],
            "acl_protected": []
        }
        for acln in acl_namespaces:
            if acln['name'] == ns_name:
                ns['admin_membership'] = get_group_membership(keycloak_admin, acln['id'])
                break
        
        ns['view_membership'] = get_group_membership(keycloak_admin, ns_id)
        ns['attributes'] = get_group_attributes(keycloak_admin, ns_id)
        ns['service_accounts'] = get_service_accounts(keycloak_admin, ns_name)
        ns['acl_protected'] = get_acl_protected_services_by_ns(ns_name, all_plugins)
        response.append(ns)

    return make_response(jsonify(response))


def get_acl_protected_services_by_ns(ns, all_plugins):
    result = []
    for svc in get_services_by_ns(ns):
        definition = {
            "name": svc['name'],
            "acl_allow": []
        }
        print("--", svc['name'])
        for rte in get_routes_by_ns(ns):
            for plugin in get_plugins_by_route(all_plugins, rte['id']):
                if plugin['name'] == 'acl':
                    definition['acl_allow'] = definition['acl_allow'] + plugin['config']['allow']
                    print("   ", plugin['config']['allow'])
        for plugin in get_plugins_by_service(all_plugins, svc['id']):
            if plugin['name'] == 'acl':
                definition['acl_allow'] = definition['acl_allow'] + plugin['config']['allow']
                print("   ", plugin['config']['allow'])

        if len(definition['acl_allow']) > 0:
            items = definition['acl_allow']
            definition['acl_allow'] = list(dict.fromkeys(items))
            result.append(definition)
    
    return result

def get_plugins_by_route(all_plugins, id):
    plugins = []
    for plugin in all_plugins:
        if plugin['route'] is not None and plugin['route']['id'] == id:
            plugins.append(plugin)
    return plugins

def get_plugins_by_service(all_plugins, id):
    plugins = []
    for plugin in all_plugins:
        if plugin['service'] is not None and plugin['service']['id'] == id:
            plugins.append(plugin)
    return plugins

def get_group_membership(keycloak_admin, id):
    members = []
    _members = keycloak_admin.get_group_members(group_id=id)
    for member in _members:
        members.append(member['username'])
    return members

def get_group_attributes(keycloak_admin, id):
    group = keycloak_admin.get_group(group_id=id)
    return group['attributes']

def get_namespaces(keycloak_admin):
    groups = keycloak_admin.get_groups()
    for group in groups:
        if group['name'] == 'ns':
            return group['subGroups']
    return None

def get_acl_namespaces(keycloak_admin):
    groups = keycloak_admin.get_groups()
    for group in groups:
        if group['name'] == 'ns-admins':
            return group['subGroups']
    return None

def get_service_accounts (keycloak_admin, namespace):
    params_path = {"realm-name": keycloak_admin.realm_name}
    data_raw = keycloak_admin.raw_get(URL_ADMIN_CLIENTS.format(**params_path), clientId='sa-%s-' % namespace, search=True)
    response = raise_error_from_response(data_raw, KeycloakGetError)
    result = []
    for r in response:
        if client_id_valid(namespace, r['clientId']):
            result.append({"clientId":r['clientId'],"enabled":r['enabled']})
    return result