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
import shutil
from keycloak.exceptions import KeycloakGetError
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
           methods=['POST'], strict_slashes=False)
@admin_jwt(None)
def create_service_account(namespace: str) -> object:
    enforce_authorization(namespace)

    f = open("templates/keycloak/client.json", "r")
    j = json.loads(f.read())

    ns = g.principal['team']
    cid = "ns-%s" % ns

    j['clientId'] = cid
    j['protocolMappers'][0]['config']['claim.value'] = ns

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

    cid = "ns-%s" % namespace

    if client_id != cid:
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
