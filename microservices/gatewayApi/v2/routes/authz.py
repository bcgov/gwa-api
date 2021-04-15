import os
import shutil
from subprocess import Popen, PIPE
import uuid
import logging
import yaml
from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app
from io import TextIOWrapper

from v2.auth.auth import admin_jwt
from clients.kcprotect import check_permissions, map_res_name_to_id, get_token

authz = Blueprint('authz', 'authz')

@authz.route('<string:resource>/<string:scope>',
           methods=['GET'], strict_slashes=False)
@admin_jwt(None)
def authz_check(resource: str, scope: str) -> object:

    pat = get_token()
    rsid = map_res_name_to_id (pat['access_token'], resource)
    answer = check_permissions (g.token_string, [("permission", "%s#%s" % ( rsid, scope ))])

    decision = 'Deny'
    if answer:
        decision = 'Allow'

    return make_response(jsonify({'decision': decision}))
