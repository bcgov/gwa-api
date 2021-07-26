from logging import error
import sys
from typing import Any
from flask import json, make_response, jsonify, abort, current_app as app
import requests

class GatewayConsumerService:

    def add_consumer_plugin(self, consumer_id: str, plugin_data: Any):
        url = app.config['kongAdminUrl'] + '/consumers/' + consumer_id + '/plugins'

        if plugin_data['name'] == 'rate-limiting':
            plugin_data = add_redis_config(plugin_data)

        return make_http_request("ADDING CONSUMER PLUGIN", consumer_id, "post", url=url, json=plugin_data, headers={'Content-Type': 'application/json'}, timeout=5)

    def update_consumer_plugin(self, consumer_id: str, plugin_id: str, plugin_data: Any):
        url = app.config['kongAdminUrl'] + '/consumers/' + consumer_id + '/plugins/' + plugin_id

        if plugin_data['name'] == 'rate-limiting':
            plugin_data = add_redis_config(plugin_data)

        return make_http_request("UPDATING CONSUMER PLUGIN", consumer_id, "put", url=url, json=plugin_data, headers={'Content-Type': 'application/json'}, timeout=5)

    def delete_consumer_plugin(self, consumer_id: str, plugin_id: str):    
        url = app.config['kongAdminUrl'] + '/consumers/' + consumer_id + '/plugins/' + plugin_id
        return make_http_request("DELETING CONSUMER PLUGIN", consumer_id, "delete", url=url, headers={'Content-Type': 'application/json'}, timeout=5)

    def get_consumer (self, id_or_name: str):
        url = app.config['kongAdminUrl'] + '/consumers/' + id_or_name
        return requests.get(url, timeout=5).json()

    def get_consumers_by_ns (self, namespace: str):
        url = app.config['kongAdminUrl'] + '/consumers?tags=ns.' + namespace
        return requests.get(url, timeout=5).json()

    def get_consumer_acl_by_ns (self, consumer_id: str, namespace: str):
        url = app.config['kongAdminUrl'] + '/consumers/' + consumer_id + '/acls?tags=ns.' + namespace
        return requests.get(url, timeout=5).json()

    def get_consumer_plugin (self, consumer_id: str, plugin_id: str):
        url = app.config['kongAdminUrl'] + '/consumers/' + consumer_id + '/plugins/' + plugin_id
        return requests.get(url, timeout=5).json()

    def create_consumer(self, consumer_data: Any):
        url = app.config['kongAdminUrl'] + '/consumers'
        return make_http_request("CREATING CONSUMER", consumer_data['username'], "post", url=url, json=consumer_data, headers={'Content-Type': 'application/json'}, timeout=5)

    def update_consumer(self, username: str, consumer_data: Any):
        url = app.config['kongAdminUrl'] + '/consumers/' + username
        return make_http_request("UPDATING CONSUMER", consumer_data['username'], "put", url=url, json=consumer_data, headers={'Content-Type': 'application/json'}, timeout=5)

    def delete_consumer(self, id_or_name: str):
        url = app.config['kongAdminUrl'] + '/consumers/' + id_or_name
        return make_http_request("DELETING CONSUMER", id_or_name, "delete", url=url, headers={'Content-Type': 'application/json'}, timeout=5)

    def add_consumer_acl(self, consumer_id, acl_data: Any):
        url = app.config['kongAdminUrl'] + '/consumers/' + consumer_id + "/acls"
        return make_http_request("ADDING CONSUMER ACL", consumer_id, "post", url=url, json=acl_data, headers={'Content-Type': 'application/json'}, timeout=5)

    def delete_consumer_acl(self, consumer_id: str, acl_id: str):
        url = app.config['kongAdminUrl'] + '/consumers/' + consumer_id + "/acls/" + acl_id
        return make_http_request("DELETING CONSUMER ACL", consumer_id, "delete", url=url, headers={'Content-Type': 'application/json'}, timeout=5)
        
    def add_keyauth_to_consumer(self, consumer_id: str, keyauth_data: Any):
        url = app.config['kongAdminUrl'] + '/consumers/' + consumer_id + '/key-auth'
        return make_http_request("ADDING KEYAUTH TO CONSUMER", consumer_id, "post", url=url, json=keyauth_data, headers={'Content-Type': 'application/json'}, timeout=5)

    def gen_key_for_consumer_keyauth(self, consumer_id: str, keyauth_id: str, key_data: Any):
        url = app.config['kongAdminUrl'] + '/consumers/' + consumer_id + '/key-auth/' + keyauth_id
        return make_http_request("GENERATING KEYAUTH KEY", consumer_id, "put", url=url, json=key_data, headers={'Content-Type': 'application/json'}, timeout=5)

def response_transformer(response):
    """ 
    Response is update with correct HTTP Error as Kong return 200 for all the requests made
    """
    if 'code' in response:
        response['http_error'] = get_http_error_by_kong_code(response['code'])
    return response
                
def get_http_error_by_kong_code(code: int):
    code_dict = {5: 409, 2: 400}
    return code_dict.get(code, 400)



def add_redis_config(pluginData: str):
    rateLimitConfig = app.config['plugins']['rate_limiting']
    pluginData['config']['redis_host'] = rateLimitConfig['redis_host']
    pluginData['config']['redis_password'] = rateLimitConfig['redis_password']
    pluginData['config']['redis_port'] = rateLimitConfig['redis_port']
    pluginData['config']['redis_timeout'] = rateLimitConfig['redis_timeout']
    pluginData['config']['redis_database'] = rateLimitConfig['redis_database']
    return pluginData


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
    