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

    hosts = []
    for route in all_routes:
        if 'hosts' in route:
            for host in route['hosts']:
                if host not in hosts:
                    hosts.append(host)

    hosts.sort()

    result = []
    for host in hosts:
        result.append("%s %s" % (fixed_ip, host))
    return Response(response="%s\n\n" % "\n".join(result), status=200, mimetype="text/plain")


@dns.route('/headers',
           methods=['GET'], strict_slashes=False)
def req_route() -> object:

    out = dict(request.headers)
    out['ip'] = request.remote_addr
    return Response(response=yaml.dump(out, indent=4), status=200, mimetype="text/plain")
