import os
import shutil
from subprocess import Popen, PIPE
import uuid
import logging
import yaml
from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app
from io import TextIOWrapper

from v1.auth.auth import admin_jwt, ns_claim
from clients.kcprotect import check_permissions

_ns_claim = ns_claim()

whoami = Blueprint('whoami', 'whoami')

@whoami.route('',
           methods=['GET'], strict_slashes=False)
@admin_jwt(None)
def who_am_i() -> object:
    """
    :return: JSON of some key information about the authenticated principal
    """

    print("Answer = %s" % check_permissions (g.token_string, [("permission", "f2dab0ff-f9e9-466d-a115-52010a1bb47d#client-manager")]))
    log = app.logger

    if _ns_claim not in g.principal:
        abort(make_response(jsonify(error="Missing Claims."), 500))

    output = {
        "authorized-party": g.principal['azp'],
        "scope": g.principal['scope'],
        "issuer": g.principal['iss'],
        "namespace": g.principal[_ns_claim],
    }
    if ('aud' in g.principal):
        output['audience'] = g.principal['aud']
    if ('clientAddress' in g.principal):
        output['client-address'] = g.principal['clientAddress']
    return make_response(jsonify(output))
