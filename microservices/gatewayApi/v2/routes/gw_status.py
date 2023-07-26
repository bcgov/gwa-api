import requests
import sys
import traceback
import urllib3
import certifi
import socket
from urllib.parse import urlparse
from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app

from v2.auth.auth import admin_jwt, uma_enforce

from clients.kong import get_services_by_ns, get_routes_by_ns

gw_status = Blueprint('gw_status_v2', 'gw_status')

@gw_status.route('',
           methods=['GET'], strict_slashes=False)
@admin_jwt(None)
@uma_enforce('namespace', 'GatewayConfig.Publish')
def get_statuses(namespace: str) -> object:

    log = app.logger

    log.info("Get status for %s" % namespace)

    services = get_services_by_ns (namespace)
    routes = get_routes_by_ns (namespace)

    response = []

    for service in services:
        url = build_url (service)
        status = "UP"
        reason = ""

        actual_host = None
        host = None
        for route in routes:
            if route['service']['id'] == service['id'] and 'hosts' in route:
                actual_host = route['hosts'][0]
                host = clean_host(actual_host)

        try:
            addr = socket.gethostbyname(service['host'])
            log.info("Address = %s" % addr)
        except:
            status = "DOWN"
            reason = "DNS"

        if status == "UP":
            try:
                headers = {}
                if host is None or service['host'].endswith('.svc'):
                    r = requests.get(url, headers=headers, timeout=3.0)
                    status_code = r.status_code
                else:
                    u = urlparse(url)

                    if service['preserve_host']:
                        headers['Host'] = host
                    else:
                        headers['Host'] = u.hostname

                    log.info("GET %-30s %s" % ("%s://%s" % (u.scheme, u.netloc), headers))

                    urllib3.disable_warnings()
                    if u.scheme == "https":
                        pool = urllib3.HTTPSConnectionPool(
                            "%s" % (u.netloc),
                            assert_hostname=host,
                            server_hostname=host,
                            cert_reqs='CERT_NONE',
                            ca_certs=certifi.where()
                        )
                    else:
                        pool = urllib3.HTTPConnectionPool(
                            "%s" % (u.netloc)
                        )
                    req = pool.urlopen(
                        "GET",
                        u.path,
                        headers={"Host": host},
                        assert_same_host=False,
                        timeout=1.0,
                        retries=False
                    )

                    status_code = req.status

                log.info("Result received!! %d" % status_code)
                if status_code < 400:
                    status =  "UP"
                    reason = "%d Response" % status_code
                elif status_code == 401 or status_code == 403:
                    status = "UP"
                    reason = "AUTH %d" % status_code
                else:
                    status =  "DOWN"
                    reason = "%d Response" % status_code
            except requests.exceptions.Timeout as ex:
                status = "DOWN"
                reason = "TIMEOUT"
            except urllib3.exceptions.ConnectTimeoutError as ex:
                status = "DOWN"
                reason = "TIMEOUT"
            except requests.exceptions.ConnectionError as ex:
                log.error("ConnError %s" % ex)
                status = "DOWN"
                reason = "CONNECTION"
            except requests.exceptions.SSLError as ex:
                status = "DOWN"
                reason = "SSL"
            except urllib3.exceptions.NewConnectionError as ex:
                log.error("NewConnError %s" % ex)
                status = "DOWN"
                reason = "CON_ERR"
            except urllib3.exceptions.SSLError as ex:
                log.error(ex)
                status = "DOWN"
                reason = "SSL_URLLIB3"
            except Exception as ex:
                log.error(ex)
                traceback.print_exc(file=sys.stdout)
                status = "DOWN"
                reason = "UNKNOWN"

        log.info("GET %-30s %s" % (url,reason))
        response.append({"name": service['name'], "upstream": url, "status": status, "reason": reason, "host": host, "env_host": actual_host})

    return make_response(jsonify(response))

def build_url (s):
    schema = default(s, "protocol", "http")
    defaultPort = 80
    if schema == "https":
        defaultPort = 443
    host = s['host']
    port = default(s, "port", defaultPort)
    path = default(s, "path", "/")
    if 'url' in s:
        return s['url']
    else:
        return "%s://%s:%d%s" % (schema, host, port, path)


def default (s, key, val):
    if key in s and s[key] is not None:
        return s[key]
    else:
        return val


def clean_host (host):
    conf = app.config['hostTransformation']
    if conf['enabled'] is True:
        conf = app.config['hostTransformation']
        return host.replace(conf['baseUrl'], 'gov.bc.ca').replace('-data-gov-bc-ca', '.data').replace('-api-gov-bc-ca', '.api').replace('-apps-gov-bc-ca', '.apps')
    else:
        return host
