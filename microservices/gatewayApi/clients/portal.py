from flask import current_app as app
import sys
import requests
import traceback
import urllib.parse

#
# 'type', 'name', 'action', 'message', 'refId', 'namespace'

def record_custom_event (uuid, type, action, result, namespace, message = ""):
    record_activity ({
        'id': uuid,
        'type': type,
        'action': action,
        'result': result,
        'name': 'N/A',
        'message': message,
        'refId': '',
        'namespace': namespace
    })

def record_namespace_event (uuid, action, result, namespace, message = ""):
    record_activity ({
        'id': uuid,
        'type': 'GatewayNamespace',
        'action': action,
        'result': result,
        'name': 'N/A',
        'message': message,
        'refId': '',
        'namespace': namespace
})

def record_gateway_event (uuid, action, result, namespace, message = ""):
    record_activity ({
        'id': uuid,
        'type': 'GatewayConfig',
        'action': action,
        'result': result,
        'name': 'N/A',
        'message': message,
        'refId': '',
        'namespace': namespace
    })

def record_activity (activity):
    log = app.logger
    portal_url = app.config['portal']['url']

    log.debug("record_activity %s : %s %s" % (portal_url, activity['id'], activity['result']))

    if portal_url != "":
        headers = {
            "Content-Type": "application/json"
        }
        try:
            r = requests.put("%s/feed/Activity" % portal_url, headers=headers, json=activity, timeout=5)
            log.info("Request Record Activity %s : %d" % (portal_url, r.status_code))
        except Exception as ex:
            log.error("Error recording activity %s : %s" % (portal_url, str(ex)))
            traceback.print_exc(file=sys.stdout)