from typing import Any
from flask import make_response, jsonify, current_app as app
import requests


class GatewayConsumerService:

    def add_consumer_plugin(self, consumer_id: str, plugin_data: Any):
        url = app.config['kongAdminUrl'] + '/consumers/' + consumer_id + '/plugins'
        return make_http_request("ADDING CONSUMER PLUGIN", consumer_id, "post", url=url, json=plugin_data, headers={'Content-Type': 'application/json'}, timeout=5)

    def update_consumer_plugin(self, consumer_id: str, plugin_id: str, plugin_data: Any):
        url = app.config['kongAdminUrl'] + '/consumers/' + consumer_id + '/plugins/' + plugin_id
        return make_http_request("UPDATING CONSUMER PLUGIN", consumer_id, "put", url=url, json=plugin_data, headers={'Content-Type': 'application/json'}, timeout=5)

    def delete_consumer_plugin(self, consumer_id: str, plugin_id: str):
        url = app.config['kongAdminUrl'] + '/consumers/' + consumer_id + '/plugins/' + plugin_id
        return make_http_request("DELETING CONSUMER PLUGIN", consumer_id, "delete", url=url, headers={'Content-Type': 'application/json'}, timeout=5)

    def get_consumer_plugin(self, consumer_id: str, plugin_id: str):
        url = app.config['kongAdminUrl'] + '/consumers/' + consumer_id + '/plugins/' + plugin_id
        return requests.get(url, timeout=5).json()


def make_http_request(action: str, id: str, method: str, **rqst_params):
    log = app.logger
    message = "STARTED"
    log.debug("%s %s[%s]" % (message, action, id))
    mod = __import__('requests')
    method_to_call = getattr(mod, method)
    response = method_to_call(**rqst_params)
    message = "COMPLETED"
    if response.status_code in (200, 201):
        res = response.json()
    elif response.status_code == 204:
        res = make_response(jsonify(message='done'), response.status_code)
    else:
        message = "FAILED"
        try:
            res = make_response(response.json(), response.status_code)
        except:
            res = make_response(jsonify(error='failed'), response.status_code)
    log.debug("%s %s[%s]" % (message, action, id))
    return res
