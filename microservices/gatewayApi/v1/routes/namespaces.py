
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

from v1.services.namespaces import NamespaceService, get_base_group_path

from v1.auth.auth import admin_jwt, enforce_authorization, enforce_role_authorization, users_group_root, admins_group_root

from clients.keycloak import admin_api
from utils.validators import namespace_valid, namespace_validation_rule

ns = Blueprint('namespaces', 'namespaces')


@ns.route('',
           methods=['POST'], strict_slashes=False)
@admin_jwt(None)
def create_namespace() -> object:
    log = app.logger

    keycloak_admin = admin_api()

    namespace = request.get_json(force=True)['name']

    if not namespace_valid(namespace):
        log.error("Namespace validation failed %s" % namespace)
        abort(make_response(jsonify(error="Namespace name validation failed.  Reference regular expression '%s'." % namespace_validation_rule), 400))

    try:
        svc = NamespaceService()

        username = None
        if 'preferred_username' in g.principal:
            username = g.principal['preferred_username']

        svc.create_or_get_ns (namespace, username)

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
           methods=['PUT'], strict_slashes=False)
@admin_jwt(None)
def update_namespace(namespace: str) -> object:
    log = app.logger
    enforce_authorization(namespace)

    params = request.get_json(force=True)

    if not namespace_valid(namespace):
        log.error("Namespace validation failed %s" % namespace)
        abort(make_response(jsonify(error="Namespace name validation failed.  Reference regular expression '%s'." % namespace_validation_rule), 400))

    try:
        svc = NamespaceService()

        ns_group = svc.get_namespace (namespace)

        svc.update_ns_attributes (ns_group, params)

    except KeycloakGetError as err:
        log.error("Failed to update namespace %s" % namespace)
        log.error(err)
        abort(make_response(jsonify(error="Failed to update namespace"), 400))

    return make_response(jsonify())

@ns.route('/<string:namespace>',
           methods=['DELETE'], strict_slashes=False)
@admin_jwt(None)
def delete_namespace(namespace: str) -> object:
    log = app.logger
    enforce_authorization(namespace)

    keycloak_admin = admin_api()

    try:
        for role_name in ['viewer', 'admin']:
            group = keycloak_admin.get_group_by_path("%s/%s" % (get_base_group_path(role_name), namespace), search_in_subgroups=True)
            if group is not None:
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
    enforce_authorization(namespace)

    desired_membership_list = json.loads(request.get_data())

    ucounts_added, ucounts_removed, ucounts_missing = membership_sync (namespace, 'viewer', desired_membership_list)
    acounts_added, acounts_removed, acounts_missing = membership_sync (namespace, 'admin', desired_membership_list)

    return make_response(jsonify(added=ucounts_added + acounts_added, removed=ucounts_removed + acounts_removed, missing=ucounts_missing + acounts_missing))

def update_pending_registrations(group, unregistered_users):
    if 'attributes' in group:
        attrs = group['attributes']
    else:
        attrs = group['attributes'] = {}

    attrs['pending'] = unregistered_users

    keycloak_admin = admin_api()
    keycloak_admin.update_group (group['id'], group)


def membership_sync (namespace, role_name, desired_membership_list):
    log = app.logger

    desired_membership = []
    for user in desired_membership_list:
        if role_name in user['roles']:
            desired_membership.append(user['username'])

    keycloak_admin = admin_api()

    base_group_path = get_base_group_path (role_name)

    group = keycloak_admin.get_group_by_path("%s/%s" % (base_group_path, namespace), search_in_subgroups=True)

    if group is None:
        log.warn("[%s] Group %s/%s Missing!" % (namespace, base_group_path, namespace))
        create_group (namespace, base_group_path, role_name)
        group = keycloak_admin.get_group_by_path("%s/%s" % (base_group_path, namespace), search_in_subgroups=True)

    membership = keycloak_admin.get_group_members (group['id'])

    counts_removed = 0
    counts_added = 0
    counts_missing = 0
    # Remove users that are not part of the provided membership
    for member in membership:
        if member['username'] not in desired_membership:
            log.debug("[%s] REMOVE user %s from %s" % (namespace, member['username'], base_group_path))
            keycloak_admin.group_user_remove (member['id'], group['id'])
            counts_removed = counts_removed + 1
        else:
            desired_membership.remove(member['username'])

    # Add missing users to the membership
    unregistered_users = []
    for username in desired_membership:
        user_id = keycloak_admin.get_user_id (username)
        if user_id is None:
            log.debug("[%s] UNREGISTERED user %s FROM %s" % (namespace, username, base_group_path))
            counts_missing = counts_missing + 1
            unregistered_users.append(username)
        else:
            log.debug("[%s] ADDING user %s TO %s" % (namespace, username, base_group_path))
            keycloak_admin.group_user_add (user_id, group['id'])
            counts_added = counts_added + 1

    # Update the pending attribute with users that are not registered yet
    update_pending_registrations (group, unregistered_users)

    return counts_added, counts_removed, counts_missing


def create_group(namespace, group_base_path, role_name):
    log = app.logger
    keycloak_admin = admin_api()

    parent_group = keycloak_admin.get_group_by_path(group_base_path)
    if parent_group is None:
        keycloak_admin.create_group ({"name": get_base_group_name(role_name)})
        parent_group = keycloak_admin.get_group_by_path(group_base_path)

    response = keycloak_admin.create_group ({"name": namespace}, parent=parent_group['id'])
    log.debug("[%s] Group %s/%s created!" % (namespace, group_base_path, namespace))

