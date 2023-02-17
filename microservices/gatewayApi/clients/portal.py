from flask import g, current_app as app
import sys
import requests
import traceback
import urllib.parse
import uuid

#
# 'type', 'name', 'action', 'message', 'refId', 'namespace'


def record_custom_event(event_id, type, action, result, namespace, message=""):
    record_activity({
        'id': event_id,
        'type': type,
        'action': action,
        'result': result,
        'name': 'N/A',
        'message': message,
        'refId': '',
        'namespace': namespace
    })


def record_namespace_event(event_id, action, result, namespace, message=""):
    record_activity({
        'id': event_id,
        'type': 'GatewayNamespace',
        'action': action,
        'result': result,
        'name': 'N/A',
        'message': message,
        'refId': '',
        'namespace': namespace
    })


def record_gateway_event(event_id, action, result, namespace, message="", blob=""):

    entity = 'gateway configuration'

    payload = {
        'id': event_id,
        'type': 'GatewayConfig',
        'action': action,
        'result': result,
        'name': 'N/A',
        'message': "%s %s" % (action, entity),
        'refId': '',
        'namespace': namespace,
        'context': {
          'message': '{actor} {action} {entity} {message}',
          'params': {
            'result': result,
            'message': message,
            'action': action,
            'entity': entity,
            'actor': g.principal["clientId"]
          }
        },
        'filterKey1': 'namespace:%s' % namespace
    }

    if not blob == "" and not blob == None:
        payload.update({'blob': [{"id": str(uuid.uuid4()), "blob": blob}]})

    record_activity(payload)


def record_activity(activity):
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
