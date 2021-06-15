from flask import current_app as app
import requests
import urllib.parse

# Access the Kong Admin API for details about the Kong configuration
#
# Use the Route Hosts found in Kong to ensure there are no conflicts
def get_routes ():
    return recurse_get_records ([], "/routes")

def get_plugins ():
    return recurse_get_records ([], "/plugins")

def get_services_by_ns (ns):
    return recurse_get_records ([], "/services?tags=ns.%s" % ns)

def get_plugins_by_service (svc):
    return recurse_get_records ([], "/services/%s/plugins" % svc)

def get_plugins_by_route (route):
    return recurse_get_records ([], "/routes/%s/plugins" % route)

def get_routes_by_ns (ns):
    return recurse_get_records ([], "/routes?tags=ns.%s" % ns)

def get_service_routes (service_id):
    return recurse_get_records ([], "/services/%s/routes" % service_id)

def recurse_get_records (result, url):
    log = app.logger
    admin_url = app.config['kongAdminUrl']

    log.debug("%s%s" % (admin_url, url))
    r = requests.get("%s%s" % (admin_url, url))
    json =  r.json()
    data = json['data']
    result.extend(data)

    if json['next'] is not None:
        recurse_get_records (result, json['next'])
    return result