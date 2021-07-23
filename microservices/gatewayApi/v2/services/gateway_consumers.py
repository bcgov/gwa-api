import sys
from flask import make_response, current_app as app
import requests

class GatewayConsumerService:

    def add_plugin_to_consumer(self, consumerid, pluginData):
        log = app.logger
        action = "ADDING CONSUMER PLUGIN"
        log.debug("%s[%s] to %s" % (action, pluginData['name'], consumerid))

        url = app.config['kongAdminUrl'] + '/consumers/' + consumerid + '/plugins'
        if pluginData['name'] == 'rate-limiting':
            pluginData = add_redis_config(pluginData)
        response = requests.post(url, json=pluginData, headers={'Content-Type': 'application/json'}, timeout=5)

        message = "COMPLETED" if response.status_code in (200, 201) else "FAILED"
            
        log.debug("%s %s[%s] to %s" % (message, action, pluginData['name'], consumerid))
        return response_transformer(response.json())

    def update_plugin_to_consumer(self, consumerid, pluginid, pluginData):
        log = app.logger
        action = "UPDATING CONSUMER PLUGIN"
        log.debug("%s[%s] to %s" % (action, pluginData['name'], consumerid))
        url = app.config['kongAdminUrl'] + '/consumers/' + consumerid + '/plugins/' + pluginid

        if pluginData['name'] == 'rate-limiting':
            pluginData = add_redis_config(pluginData)

        response = requests.put(url, json=pluginData, headers={'Content-Type': 'application/json'}, timeout=5)
        message = "COMPLETED" if response.status_code in (200, 201) else "FAILED"           
        log.debug("%s %s[%s] to %s" % (message, action, pluginData['name'], consumerid))
        return response.json()

    def delete_plugin_to_consumer(self, consumerid, pluginid):
        log = app.logger
        action = "DELETING CONSUMER PLUGIN"
        try:
            res = self.get_gateway_consumer_plugin(consumerid, pluginid)
        except:
            log.error("failed to fetch plugin. %s" % sys.exc_info()[0])

        if "message" in res:
            log.error("failed to fetch plugin. %s" % res['message'])
            return res

        log.debug("%s[%s] from %s" % (action, res['name'], consumerid))
        url = app.config['kongAdminUrl'] + '/consumers/' + consumerid + '/plugins/' + pluginid
        response = requests.delete(url, headers={'Content-Type': 'application/json'}, timeout=5)
        message = "COMPLETED" if response.status_code == 204 else "FAILED"
        log.debug("%s %s[%s] from %s" % (message, action, res['name'], consumerid))
        return make_response('deleted', response.status_code)

    def get_gateway_consumer (self, consumer_id):
        url = app.config['kongAdminUrl'] + '/consumers/' + consumer_id
        response = requests.get(url, timeout=5)
        return response.json()

    def get_gateway_consumer_plugin (self, consumer_id, plugin_id):
        url = app.config['kongAdminUrl'] + '/consumers/' + consumer_id + '/plugins/' + plugin_id
        response = requests.get(url, timeout=5)
        return response.json()

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