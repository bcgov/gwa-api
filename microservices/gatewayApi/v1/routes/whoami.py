import os
import shutil
from subprocess import Popen, PIPE
import uuid
import logging
import yaml
from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app
from io import TextIOWrapper

from v1.auth.auth import admin_jwt, ns_claim

_ns_claim = ns_claim()

whoami = Blueprint('whoami', 'whoami')

@whoami.route('',
           methods=['GET'], strict_slashes=False)
@admin_jwt(None)
def who_am_i() -> object:
    """
    :return: JSON of some key information about the authenticated principal
    """
    log = app.logger

    if _ns_claim not in g.principal:
        abort(make_response(jsonify(error="Missing Claims."), 500))

    output = {
        "authorized-party": g.principal['azp'],
        "scope": g.principal['scope'],
        "issuer": g.principal['iss'],
        # "audience": g.principal['aud'],
        "namespace": g.principal[_ns_claim],
        "client-address": g.principal['clientAddress'],
    }

    return make_response(jsonify(output))
