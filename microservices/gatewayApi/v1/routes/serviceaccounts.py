#
# Service Accounts
# This API allows an authorized user to manage Clients
# for a namespace with particular access rights / scopes
# such as:
# - gateway:manage    : ability to submit config to Kong
# - namespace:create  : ability to create a namespace
# - namespace:update  : ability to update some namespace details
# - membership:manage : ability to manage the namespace membership
#
import os
import string
import random
import shutil
from keycloak.exceptions import raise_error_from_response, KeycloakGetError
from keycloak.urls_patterns import URL_ADMIN_CLIENTS
from subprocess import Popen, PIPE, STDOUT
import uuid
import logging
import json
import yaml
from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app
from io import TextIOWrapper

from clients.keycloak import admin_api
from v1.auth.auth import admin_jwt, enforce_authorization

sa = Blueprint('serviceaccounts', 'serviceaccounts')

@sa.route('',
           methods=['GET'], strict_slashes=False)
@admin_jwt(None)
def list_service_accounts(namespace: str) -> object:
    enforce_authorization(namespace)

    ns = g.principal['team']

    keycloak_admin = admin_api()

    try:
        params_path = {"realm-name": keycloak_admin.realm_name}
        data_raw = keycloak_admin.raw_get(URL_ADMIN_CLIENTS.format(**params_path), clientId='sa-%s-' % ns, search=True)
        response = raise_error_from_response(data_raw, KeycloakGetError)
        result = []
        for r in response:
            result.append(r['clientId'])
        return (json.dumps(result), 200)
    except KeycloakGetError as err:
        log.error(err)
        abort(make_response(jsonify(error="Failed to read service accounts"), 400))


@sa.route('',
           methods=['POST'], strict_slashes=False)
@admin_jwt(None)
def create_service_account(namespace: str) -> object:
    enforce_authorization(namespace)

    f = open("templates/keycloak/client.json", "r")
    j = json.loads(f.read())

    cid = "sa-%s-%s" % (namespace, get_random_string(10))

    j['clientId'] = cid
    j['protocolMappers'][0]['config']['claim.value'] = namespace

    keycloak_admin = admin_api()

    try:
        response = keycloak_admin.create_client (j)
        cuuid = keycloak_admin.get_client_id(cid)
        r = keycloak_admin.generate_client_secrets(cuuid)
        return ({'client_id': cid, 'client_secret': r['value']}, 201)
    except KeycloakGetError as err:
        if err.response_code == 409:
            abort(make_response(jsonify(error="Service Account for this namespace is already created."), 400))
        else:
            log.error(err)
            abort(make_response(jsonify(error="Failed to add service account"), 400))

@sa.route('/<string:client_id>',
           methods=['PUT'], strict_slashes=False)
@admin_jwt(None)
def update_service_account_credentials(namespace: str, client_id: str) -> object:
    enforce_authorization(namespace)

    cid = "sa-%s-" % namespace

    if not client_id.startswith(cid):
        abort(make_response(jsonify(error="Invalid client ID"), 400))

    keycloak_admin = admin_api()

    try:
        cuuid = keycloak_admin.get_client_id(cid)
        r = keycloak_admin.generate_client_secrets(cuuid)
        return ({'client_id': cid, 'client_secret': r['value']}, 201)
    except KeycloakGetError as err:
        if err.response_code == 409:
            abort(make_response(jsonify(error="Service Account for this namespace is already created."), 400))
        else:
            log.error(err)
            abort(make_response(jsonify(error="Failed to add service account"), 400))

@sa.route('/<string:client_id>',
           methods=['DELETE'], strict_slashes=False)
@admin_jwt(None)
def delete_service_account(namespace: str, client_id: str) -> object:
    enforce_authorization(namespace)

    cid = "sa-%s-" % namespace

    if not client_id.startswith(cid):
        abort(make_response(jsonify(error="Invalid client ID"), 400))

    keycloak_admin = admin_api()

    try:
        cuuid = keycloak_admin.get_client_id(client_id)
        if cuuid is None:
            abort(make_response(jsonify(error="Service Account does not exist"), 400))
        else:
            keycloak_admin.delete_client (cuuid)
            return ({}, 204)
    except KeycloakGetError as err:
        log.error(err)
        abort(make_response(jsonify(error="Failed to delete service account"), 400))

def get_random_string(length):
    letters = string.ascii_lowercase + string.digits
    result_str = ''.join(random.choice(letters) for i in range(length))
    print("Random string of length", length, "is:", result_str)
    return result_str
