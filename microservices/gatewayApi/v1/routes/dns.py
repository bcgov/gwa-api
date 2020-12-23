import os
import shutil
from subprocess import Popen, PIPE
import uuid
import logging
import yaml
from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app
from io import TextIOWrapper

from clients.kong import get_routes

from v1.auth.auth import admin_jwt, ns_claim

dns = Blueprint('dns', 'dns')

@dns.route('',
           methods=['GET'], strict_slashes=False)
def dns_route() -> object:
    """
    :return: A text output that can be added to an /etc/hosts file which includes the
    : routes that are part of the gateway.
    """
    log = app.logger

    fixed_ip = "142.34.194.118"

    all_routes = get_routes()

    result = []

    for route in all_routes:
        if 'hosts' in route:
            for host in route['hosts']:
                result.append(host)
    return Response(response="%s %s\n\n" % (fixed_ip, " ".join(result)), status=200, mimetype="text/plain")

