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

def get_local_certs_by_ns (ns):
    return recurse_get_records ([], "/certificates?tags=gwa.ns.%s" % ns)

def get_public_certs_by_ns (ns):
    return recurse_get_records ([], "/certificates?tags=ns.%s" % ns)

def get_acls ():
    return recurse_get_records ([], "/acls")

def get_consumer (consumer_id):
    return get_record ([], "/consumers/%s" % consumer_id)

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

def get_record (result, url):
    log = app.logger
    admin_url = app.config['kongAdminUrl']

    log.debug("%s%s" % (admin_url, url))
    r = requests.get("%s%s" % (admin_url, url))
    return r.json()

# certs: [
#   {
#      "cert": "",
#      "key": "",
#      "snis": [ "name": "abc-host" } ]
#      "tags": [ "gwa.ns.<namespace>"]
#   } 
# ]
def register_kong_certs(namespace, certs):
    log = app.logger
    admin_url = app.config['kongAdminUrl']

    log.debug("[%s] register_kong_certs %s" % (namespace, len(certs)))
  
    all_certs_for_ns = get_local_certs_by_ns(namespace)
    log.debug("[%s] current_kong_certs %d" % (namespace, len(all_certs_for_ns) ))    

    for cert in all_certs_for_ns:
      if len(cert['snis']) != 1:
        raise Exception("Expecting exactly one SNI per certificate from existing Kong certs")

      for sni in cert['snis']:
        log.debug("[%s] %s" % (namespace, sni))

        if find_cert_sni_in_list(sni, certs) is None:
          r = requests.delete("%s%s" % (admin_url, "/certificates/%s" % cert['id']))
          r.raise_for_status()
          log.debug("[%s] DELETED %s" % (namespace, sni))

    headers = { "Content-Type": "application/json" }
    for cert in certs:
      if len(cert['snis']) != 1:
        raise Exception("Expecting exactly one SNI per certificate")

      existing_cert = find_cert_sni_in_list(cert['snis'][0], all_certs_for_ns)
      if existing_cert is None:
        r = requests.post("%s%s" % (admin_url, "/certificates"), headers=headers, json=cert)
        r.raise_for_status()
        if r.status_code == 200 or r.status_code == 201:
          log.debug("[%s] CREATED %s" % (namespace, cert['snis'][0]))
      elif existing_cert['cert'] != cert['cert']:
        r = requests.patch("%s%s" % (admin_url, "/certificates/%s" % existing_cert['id']), headers=headers, json=cert)
        r.raise_for_status()
        if r.status_code == 200 or r.status_code == 201:
          log.debug("[%s] UPDATED %s" % (namespace, cert['snis'][0]))
      else:
        log.debug("[%s] NO CHANGE %s" % (namespace, cert['snis'][0]))

def find_cert_sni_in_list (sni_name, cert_list):
    for cert in cert_list:
      for sni in cert['snis']:
        if sni == sni_name:
            return cert
    return None