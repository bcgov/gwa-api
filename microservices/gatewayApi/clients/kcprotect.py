from flask import current_app as app
import requests
import urllib.parse
import base64

def get_token ():
    conf = app.config['keycloak']

    log = app.logger

    tokenUrl = "%srealms/%s/protocol/openid-connect/token" % (conf['serverUrl'],conf['realm'])

    data = {
        "grant_type": "client_credentials",
        "client_id": conf['clientId'],
        "client_secret": conf['clientSecret']
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    r = requests.post(tokenUrl, headers=headers, data=data)
    log.debug("[get_token] %s" % r.status_code)
    json = r.json()
    return json

def map_res_name_to_id (pat_token, name):
    conf = app.config['keycloak']

    log = app.logger

    tokenUrl = "%srealms/%s/authz/protection/resource_set?name=%s" % (conf['serverUrl'],conf['realm'], name)

    headers = {
        "Authorization": "Bearer %s" % pat_token,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    log.debug("[map_res_name_to_id] %s" % name)

    r = requests.get(tokenUrl, headers=headers)
    log.debug("[map_res_name_to_id] %s" % r.status_code)
    json = r.json()
    log.debug("[map_res_name_to_id] %s" % json)
    if len(json) == 0:
        return None
    else:
        return json[0]


def check_permissions (access_token, permissions):
    conf = app.config['keycloak']

    log = app.logger

    tokenUrl = "%srealms/%s/protocol/openid-connect/token" % (conf['serverUrl'],conf['realm'])

    headers = {
        "Authorization": "Bearer %s" % access_token,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = [
        ("grant_type", "urn:ietf:params:oauth:grant-type:uma-ticket"),
        ("audience", conf['clientId']),
        ("submit_request", False),
        ("response_mode", "decision"),
    ] + permissions

    r = requests.post(tokenUrl, headers=headers, data=data)
    log.debug("[check_permissions] %s" % r.status_code)
    json = r.json()
    log.debug("[check_permissions] %s" % json)
    return ('error' in json or json['result'] == False) == False
