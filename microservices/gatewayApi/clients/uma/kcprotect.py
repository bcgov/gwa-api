from flask import current_app as app
import requests
import urllib.parse
import base64

def get_token ():
    conf = app.config['resourceAuthServer']

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

    print(tokenUrl)
    r = requests.post(tokenUrl, headers=headers, data=data)
    log.debug("[get_token] %s" % r.status_code)
    json = r.json()
    return json



def check_permissions (access_token, permissions):
    conf = app.config['resourceAuthServer']

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

    log.debug("[check_permissions] %s" % permissions)
    log.debug("[check_permissions] %s" % tokenUrl)
    r = requests.post(tokenUrl, headers=headers, data=data)
    log.debug("[check_permissions] %s" % r.status_code)
    json = r.json()
    log.debug("[check_permissions] %s" % json)
    return ('error' in json or json['result'] == False) == False
