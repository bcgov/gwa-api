from flask import current_app as app
import requests
import urllib.parse

# Access the Kong Admin API for details about the Kong configuration
#
# Use the Route Hosts found in Kong to ensure there are no conflicts
def get_routes ():
    return recurse_get_routes ([], "/routes")

def recurse_get_routes (result, url):
    log = app.logger
    admin_url = app.config['kongAdminUrl']

    log.debug("%s%s" % (admin_url, url))
    r = requests.get("%s%s" % (admin_url, url))
    json =  r.json()
    data = json['data']
    result.extend(data)

    if json['next'] is not None:
        recurse_get_routes (result, json['next'])
    return result