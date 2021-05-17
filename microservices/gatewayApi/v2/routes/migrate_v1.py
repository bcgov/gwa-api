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

mg = Blueprint('migration.v2', 'migration')

@mg.route('export',
           methods=['GET'], strict_slashes=False)
@admin_jwt('Namespace.Admin')
def export_details() -> object:
    keycloak_admin = admin_api()

    response = []
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
            "service_accounts": []
        }
        for acln in acl_namespaces:
            if acln['name'] == ns_name:
                ns['admin_membership'] = get_group_membership(keycloak_admin, acln['id'])
                break
        ns['view_membership'] = get_group_membership(keycloak_admin, ns_id)
        ns['attributes'] = get_group_attributes(keycloak_admin, ns_id)
        ns['service_accounts'] = get_service_accounts(keycloak_admin, ns_name)
        response.append(ns)

    return make_response(jsonify(response))


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