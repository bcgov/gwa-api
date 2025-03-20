
#
# Create Namespace :
#  * Add a Namespace Resource (Create ResourceSet)
#  * For legacy reasons, add as a Group (alternative, add attributes to the Resource, if possible)
#
# List Namespaces (Resources) (Query ResourceSet by "owner")
# 
# Update Namespace (attributes)
#
# Delete Namespace (if there is Gateway Configuration, then do not allow)
#  * Delete Resource
#  * Delete Group
#
import requests
import sys
import http
import traceback
import uuid
import os
import urllib3
import certifi
import socket
import json
from subprocess import Popen, PIPE, STDOUT
from urllib.parse import urlparse
from werkzeug.exceptions import HTTPException, NotFound
from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app

from v2.auth.auth import admin_jwt, uma_enforce

from clients.portal import record_gateway_event
from clients.uma.kcprotect import get_token, create_permission
from clients.uma.resourceset import list_resources, create_resource, delete_resource, map_res_name_to_id
from clients.ocp_routes import get_host_list

from utils.masking import mask

from v1.services.namespaces import NamespaceService, get_base_group_path
from utils.cleanup import cleanup
from utils.get_data_plane import get_data_plane

ns = Blueprint('namespaces_v2', 'namespaces')
local_environment = os.environ.get("LOCAL_ENVIRONMENT", default=False)

def abort_early(event_id, action, namespace, response):
    record_gateway_event(event_id, action, 'failed', namespace, json.dumps(response.get_json()))
    abort(make_response(response, 400))

@ns.route('',
           methods=['GET'], strict_slashes=False)
@admin_jwt(None)
# @uma_enforce('namespace', 'GatewayConfig.Read')
def list_namespaces() -> object:

    log = app.logger
    pat = get_token()
    print(g.principal)
    username = g.principal['preferred_username']
    print(username)
    response = list_resources(pat['access_token'], username)
    return make_response(jsonify(response))

@ns.route('/defaults',
           methods=['GET'], strict_slashes=False)
def get_namespace() -> object:

    defaults = {
      "perm-domains": [ '.api.gov.bc.ca' ],
      "perm-data-plane": app.config['defaultDataPlane'],
      "perm-protected-ns": 'deny'
    }

    return make_response(jsonify(defaults))

@ns.route('/<string:namespace>',
           methods=['DELETE'], strict_slashes=False)
@admin_jwt(None)
@uma_enforce('namespace', 'Namespace.Manage')
def delete_namespace(namespace: str) -> object:
    log = app.logger

    print(g.principal)

    pat = get_token()
    pat_token = pat['access_token']

    event_id = str(uuid.uuid4())
    record_gateway_event(event_id, 'delete', 'received', namespace)

    ns_svc = NamespaceService()
    ns_attributes = ns_svc.get_namespace_attributes(namespace)

    outFolder = namespace

    tempFolder = "%s/%s/%s" % ('/tmp', uuid.uuid4(), outFolder)
    os.makedirs(tempFolder, exist_ok=False)

    with open("%s/%s" % (tempFolder, 'empty.yaml'), 'w') as file:
        file.write("")

    selectTag = "ns.%s" % namespace
    log.debug("ST = %s" % selectTag)

    # Call the 'deck' command
    deck_cli = app.config['deckCLI']
    cmd = "sync"

    log.info("[%s] (%s) %s action using %s" % (namespace, deck_cli, cmd, selectTag))
    args = [
        deck_cli, cmd, "--config", "/tmp/deck.yaml", "--skip-consumers", "--select-tag", selectTag, "--state", tempFolder
    ]
    log.debug("[%s] Running %s" % (namespace, args))
    deck_run = Popen(args, stdout=PIPE, stderr=STDOUT)
    out, err = deck_run.communicate()
    if deck_run.returncode != 0:
        cleanup(tempFolder)
        log.warn("%s - %s" % (namespace, out.decode('utf-8')))
        abort_early(event_id, 'delete', namespace, jsonify(error="Sync Failed.", results=mask(out.decode('utf-8'))))

    elif cmd == "sync" and not local_environment:
        try:
            session = requests.Session()
            session.headers.update({"Content-Type": "application/json"})
            route_payload = {
                "hosts": get_host_list(tempFolder),
                "select_tag": selectTag,
                "ns_attributes": ns_attributes.getAttrs()
            }
            dp = get_data_plane(ns_attributes)
            rqst_url = app.config['data_planes'][dp]['kube-api']
            log.debug("[%s] - Initiating request to kube API" % (dp))
            res = session.put(rqst_url + "/namespaces/%s/routes" % namespace, json=route_payload, auth=(
                app.config['kubeApiCreds']['kubeApiUser'], app.config['kubeApiCreds']['kubeApiPass']))
            log.debug("[%s] - The kube API responded with %s" % (dp, res.status_code))
            if res.status_code != 201:
                log.debug("[%s] - The kube API could not process the request" % (dp))
                raise Exception("[%s] - Failed to apply routes: %s" % (dp, str(res.text)))
            session.close()
        except HTTPException as ex:
            traceback.print_exc()
            log.error("Error updating custom routes. %s" % ex)
            abort_early(event_id, 'delete', namespace, jsonify(error="Partially failed."))
        except:
            traceback.print_exc()
            log.error("Error updating custom routes. %s" % sys.exc_info()[0])
            abort_early(event_id, 'delete', namespace, jsonify(error="Partially failed."))

    cleanup(tempFolder)

    log.debug("[%s] The exit code was: %d" % (namespace, deck_run.returncode))

    message = "Deletion successful."

    record_gateway_event(event_id, 'delete', 'completed', namespace)

    return make_response('', http.HTTPStatus.NO_CONTENT)
