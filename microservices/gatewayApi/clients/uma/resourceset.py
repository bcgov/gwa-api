from flask import current_app as app
import requests
import urllib.parse
import base64

def get_resource (pat_token, id):
    conf = app.config['keycloak']

    log = app.logger

    url = "%srealms/%s/authz/protection/resource_set/%s" % (conf['serverUrl'],conf['realm'], id)

    headers = {
        "Authorization": "Bearer %s" % pat_token,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    log.debug("[get_resource]")

    r = requests.get(url, headers=headers)
    log.debug("[get_resource] %s" % r.status_code)
    json = r.json()
    log.debug("[v] %s" % json)
    return json

def list_resources (pat_token, owner):
    conf = app.config['keycloak']

    log = app.logger

    url = "%srealms/%s/authz/protection/resource_set?owner=%s" % (conf['serverUrl'],conf['realm'], owner)

    headers = {
        "Authorization": "Bearer %s" % pat_token,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    log.debug("[list_resources]")

    r = requests.get(url, headers=headers)
    log.debug("[list_resources] %s" % r.status_code)
    json = r.json()
    result = []
    for id in json:
        result.append(get_resource(pat_token, id))
    log.debug("[list_resources] %s" % json)
    return result

def create_resource (pat_token, owner, resName, resType, scopes):
    conf = app.config['keycloak']

    log = app.logger

    resource = {
        "name" : resName,
        "type" : resType,
        "owner" : owner,
        "ownerManagedAccess" : True,
        "resource_scopes": scopes
    }

    postUrl = "%srealms/%s/authz/protection/resource_set" % (conf['serverUrl'],conf['realm'])

    headers = {
        "Authorization": "Bearer %s" % pat_token,
        "Content-Type": "application/json"
    }

    log.debug("[create_resource]")

    r = requests.post(postUrl, headers=headers, json=resource)
    log.debug("[create_resource] %s" % r.status_code)
    json = r.json()
    log.debug("[create_resource] %s" % json)
    return json

def delete_resource (pat_token, id):
    conf = app.config['keycloak']

    log = app.logger

    url = "%srealms/%s/authz/protection/resource_set/%s" % (conf['serverUrl'],conf['realm'], id)

    headers = {
        "Authorization": "Bearer %s" % pat_token,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    log.debug("[delete_resource]")

    r = requests.delete(url, headers=headers)
    log.debug("[delete_resource] %s" % r.status_code)

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
