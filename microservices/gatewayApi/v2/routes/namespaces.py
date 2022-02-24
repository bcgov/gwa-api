
#
# Create Namespace :
#  * Add a Namespace Resource (Create ResourceSet)
#  * For legacy reasons, add as a Group (alternative, add attributes to the Resource, if possible)
#
# List Namespaces (Resources) (Query ResourceSet by "owner")
# 
# Update Namespace (attributes)
#
# Delete Namespace (if there is Gateway Configuration, then do not allow)
#  * Delete Resource
#  * Delete Group
#
import requests
import sys
import traceback
import urllib3
import certifi
import socket
from urllib.parse import urlparse
from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app

from v2.auth.auth import admin_jwt, uma_enforce

from clients.uma.kcprotect import get_token, create_permission
from clients.uma.resourceset import list_resources, create_resource, delete_resource, map_res_name_to_id

from keycloak.exceptions import KeycloakGetError
from clients.keycloak import admin_api
from utils.validators import namespace_valid, namespace_validation_rule

from v1.services.namespaces import NamespaceService, get_base_group_path


ns = Blueprint('namespaces_v2', 'namespaces')

@ns.route('',
           methods=['GET'], strict_slashes=False)
@admin_jwt(None)
# @uma_enforce('namespace', 'GatewayConfig.Read')
def list_namespaces() -> object:

    log = app.logger
    pat = get_token()
    print(g.principal)
    username = g.principal['preferred_username']
    print(username)
    response = list_resources(pat['access_token'], username)
    return make_response(jsonify(response))

@ns.route('',
           methods=['POST'], strict_slashes=False)
@admin_jwt(None)
def create_namespace() -> object:
    log = app.logger

    pat = get_token()

    namespace = request.get_json(force=True)['name']

    if not namespace_valid(namespace):
        log.error("Namespace validation failed %s", namespace)
        abort(make_response(jsonify(error="Namespace name validation failed.  Reference regular expression '%s'." % namespace_validation_rule), 400))

    try:

        # Resource owners will be the Resource Server - this is because it is quite difficult to manage
        # user-level resources in Keycloak due to the tight permission model around it.
        # For example, the Resource Server can not delete/change policies or permissions for a resource
        # owned by a different user.
        #
        svc = NamespaceService()

        # username = None
        # if 'preferred_username' in g.principal:
        #     username = g.principal['preferred_username']

        scopes = [ 'Namespace.Manage', 'Namespace.View', 'GatewayConfig.Publish', 'Access.Manage', 'Content.Publish', 'CredentialIssuer.Admin' ]
        res = create_resource (pat['access_token'], namespace, 'namespace', scopes)
        print("Resource created")
        print("Assigning Namespace.Manage to", g.principal['sub'])

        permission = {
            "resource": res['_id'],
            "requester": g.principal['sub'],
            "granted": True,
            "scopeName": 'Namespace.Manage'
        }

        create_permission (pat['access_token'], permission)
        svc.create_or_get_ns (namespace, None)

    except KeycloakGetError as err:
        if err.response_code == 409:
            log.error("Namespace %s already created." % namespace)
            log.error(err)
            abort(make_response(jsonify(error="Namespace is already created."), 400))
        else:
            log.error("Failed to create namespace %s" % namespace)
            log.error(err)
            abort(make_response(jsonify(error="Failed to add namespace"), 400))

    return ('', 201)

@ns.route('/<string:namespace>',
           methods=['DELETE'], strict_slashes=False)
@admin_jwt(None)
@uma_enforce('namespace', 'Namespace.Manage')
def delete_namespace(namespace: str) -> object:
    log = app.logger

    print(g.principal)

    pat = get_token()
    pat_token = pat['access_token']

    # keycloak_admin = admin_api()

    try:
        # for role_name in ['viewer', 'admin']:
        #     group = keycloak_admin.get_group_by_path("%s/%s" % (get_base_group_path(role_name), namespace), search_in_subgroups=True)
        #     if group is not None:
        #         keycloak_admin.delete_group (group['id'])

        rid = map_res_name_to_id (pat_token, namespace)
        delete_resource (pat_token, rid)
    except KeycloakGetError as err:
        log.error(err)
        abort(make_response(jsonify(error="Failed to delete namespace"), 400))

    return ('', 204)
