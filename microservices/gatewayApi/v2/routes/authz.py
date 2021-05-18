import os
import shutil
from subprocess import Popen, PIPE
import uuid
import logging
import yaml
from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app
from io import TextIOWrapper

from v2.auth.auth import admin_jwt, uma_enforce
from clients.uma.kcprotect import check_permissions, get_token
from clients.uma.resourceset import map_res_name_to_id

authz = Blueprint('authz', 'authz')

@authz.route('<string:resource>/<string:scope>',
           methods=['GET'], strict_slashes=False)
@admin_jwt(None)
@uma_enforce('resource', None)
def authz_check(resource: str, scope: str) -> object:
    return make_response(jsonify({'decision': True}))
