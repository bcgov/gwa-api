
# Namespaces:
# This API allows an authorized user to manage namespaces
# CRUD for namespaces.
# A namespace will be managed in Keycloak as a Group.
#
import os
import shutil
from keycloak.exceptions import KeycloakGetError
from subprocess import Popen, PIPE, STDOUT
import uuid
import logging
import json
import yaml
from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app
from io import TextIOWrapper

from v1.auth.auth import admin_jwt, enforce_authorization, enforce_role_authorization

from clients.keycloak import admin_api

ns = Blueprint('namespaces', 'namespaces')

@ns.route('',
           methods=['POST'], strict_slashes=False)
@admin_jwt(None)
def create_namespace() -> object:
    log = app.logger
    enforce_role_authorization('aps.ns:manage')

    keycloak_admin = admin_api()

    namespace = request.get_json(force=True)['name']
    payload = {
        "name": namespace
    }

    parent_group = keycloak_admin.get_group_by_path('/team')

    try:
        response = keycloak_admin.create_group (payload, parent=parent_group['id'])

        new_id = response['id']

        if 'preferred_username' in g.principal:
            user_id = keycloak_admin.get_user_id (g.principal['preferred_username'])
            log.debug("[%s] ADDING user %s" % (namespace, username))
            keycloak_admin.group_user_add (user_id, new_id)

    except KeycloakGetError as err:
        if err.response_code == 409:
            abort(make_response(jsonify(error="Namespace is already created."), 400))
        else:
            log.error(err)
            abort(make_response(jsonify(error="Failed to add namespace"), 400))

    return ('', 201)

@ns.route('/<string:namespace>',
           methods=['DELETE'], strict_slashes=False)
@admin_jwt(None)
def delete_namespace(namespace: str) -> object:
    log = app.logger
    enforce_role_authorization('aps.ns:manage')

    keycloak_admin = admin_api()

    group = keycloak_admin.get_group_by_path("/team/%s" % namespace, search_in_subgroups=True)

    if group is None:
        abort(make_response(jsonify(error="Group does not exist"), 400))

    try:
        keycloak_admin.delete_group (group['id'])

    except KeycloakGetError as err:
        log.error(err)
        abort(make_response(jsonify(error="Failed to delete namespace"), 400))

    return ('', 204)

@ns.route('/<string:namespace>/membership',
           methods=['PUT'], strict_slashes=False)
@admin_jwt(None)
def update_membership(namespace: str) -> object:
    # Sync the membership list provided with the group membership
    # in Keycloak
    #
    log = app.logger

    enforce_authorization(namespace)

    desired_membership_list = json.loads(request.get_data())
    desired_membership = []
    for user in desired_membership_list:
        desired_membership.append(user['username'])

    keycloak_admin = admin_api()

    group = keycloak_admin.get_group_by_path("/team/%s" % namespace, search_in_subgroups=True)

    membership = keycloak_admin.get_group_members (group['id'])

    counts_removed = 0
    counts_added = 0
    counts_missing = 0
    # Remove users that are not part of the provided membership
    for member in membership:
        if member['username'] not in desired_membership:
            log.debug("[%s] REMOVE user %s" % (namespace, member['username']))
            keycloak_admin.group_user_remove (member['id'], group['id'])
            counts_removed = counts_removed + 1
        else:
            desired_membership.remove(member['username'])

    # Add missing users to the membership
    unregistered_users = []
    for username in desired_membership:
        user_id = keycloak_admin.get_user_id (username)
        if user_id is None:
            log.error("[%s] UNREGISTERED user %s" % (namespace, username))
            counts_missing = counts_missing + 1
            unregistered_users.append(username)
        else:
            log.debug("[%s] ADDING user %s" % (namespace, username))
            keycloak_admin.group_user_add (user_id, group['id'])
            counts_added = counts_added + 1

    update_pending_registrations (group, unregistered_users)

    return make_response(jsonify(added=counts_added, removed=counts_removed, missing=counts_missing))

def update_pending_registrations(group, unregistered_users):
    if 'attributes' in group:
        attrs = group['attributes']
    else:
        attrs = group['attributes'] = {}

    attrs['pending'] = unregistered_users

    keycloak_admin = admin_api()
    keycloak_admin.update_group (group['id'], group)
