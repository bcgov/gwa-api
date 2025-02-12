import requests
import sys
import traceback
from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app
from werkzeug.exceptions import HTTPException

from v2.auth.auth import admin_jwt, uma_enforce
from v2.services.namespaces import NamespaceService
from utils.get_data_plane import get_data_plane
from clients.kong import get_services_by_ns, get_routes_by_ns

gw_status = Blueprint('gw_status_v2', 'gw_status')

@gw_status.route('',
           methods=['GET'], strict_slashes=False)
@admin_jwt(None)
@uma_enforce('namespace', 'GatewayConfig.Publish')
def get_statuses(namespace: str) -> object:

    log = app.logger

    log.info("Get status for %s" % namespace)

    services = get_services_by_ns(namespace)
    routes = get_routes_by_ns(namespace)

    ns_svc = NamespaceService()
    ns_attributes = ns_svc.get_namespace_attributes(namespace)

    res = []

    try:
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        service_payload = {
            "services": services,
            "routes": routes,
        }

        dp = get_data_plane(ns_attributes)
        rqst_url = app.config['data_planes'][dp]['kube-api']
        log.debug("[%s] - Initiating request to kube API" % (dp))

        res = session.get(rqst_url + "/namespaces/%s/service-status" % namespace,
                          json=service_payload,
                          auth=(app.config['kubeApiCreds']['kubeApiUser'], app.config['kubeApiCreds']['kubeApiPass']))

        log.debug("[%s] - The kube API responded with %s" % (dp, res.status_code))

        if res.status_code != 200:
            log.debug("[%s] - The kube API could not process the request" % (dp))
            raise Exception("[%s] - Failed to get services: %s" % (dp, str(res.text)))

    except HTTPException as ex:
        log.error("Error getting status of services. %s" % str(ex))
        return make_response(jsonify({"error": "HTTP exception occurred", "details": str(ex)}), 500)
    except requests.exceptions.RequestException as ex:
        log.error("Request error: %s" % str(ex))
        return make_response(jsonify({"error": "Request exception occurred", "details": str(ex)}), 500)
    except Exception as ex:
        log.error("Unexpected error occurred: %s" % str(ex))
        traceback.print_exc()
        return make_response(jsonify({"error": "Unexpected error occurred", "details": str(ex)}), 500)
    finally:
        session.close()

    return make_response(jsonify(res.json()))
