from flask import current_app as app
import copy
import json
import requests
from urllib.parse import quote, quote_plus

# JWK fields that must never leave the control-plane API.
_JWK_PRIVATE_FIELDS = ('d', 'p', 'q', 'dp', 'dq', 'qi', 'k', 'priv', 'oth')

# Access the Kong Admin API for details about the Kong configuration
#
# Use the Route Hosts found in Kong to ensure there are no conflicts
def get_routes ():
    return recurse_get_records ([], "/routes")

def get_plugins ():
    return recurse_get_records ([], "/plugins")

def get_tagged_resources_by_tag (tag, base_url = None):
    return recurse_get_records ([], "/tags/" + quote(tag), base_url=base_url)

def _public_jwk(jwk):
    """Return a public-only JWK, or None if the value cannot be sanitized."""
    parsed = None
    as_string = isinstance(jwk, str)
    if as_string:
        if not jwk.strip():
            return None
        try:
            parsed = json.loads(jwk)
        except (TypeError, ValueError):
            return None
    elif isinstance(jwk, dict):
        parsed = jwk
    else:
        return None
    if not isinstance(parsed, dict):
        return None
    for field in _JWK_PRIVATE_FIELDS:
        parsed.pop(field, None)
    if as_string:
        return json.dumps(parsed, separators=(',', ':'))
    return parsed


def strip_private_key_material(entity):
    """Return a copy of a Kong key/key-set with private material removed."""
    if entity is None:
        return entity
    cleaned = copy.deepcopy(entity)
    pem = cleaned.get('pem')
    if pem is not None:
        if isinstance(pem, dict):
            pem.pop('private_key', None)
            pem.pop('private_key_alt', None)
        else:
            # Unexpected representation — omit rather than risk leaking material.
            cleaned.pop('pem', None)
    if 'jwk' in cleaned:
        public_jwk = _public_jwk(cleaned.get('jwk'))
        if public_jwk is None:
            # Unparseable or non-object JWK — omit rather than return unsanitized material.
            cleaned.pop('jwk', None)
        else:
            cleaned['jwk'] = public_jwk
    nested_keys = cleaned.get('keys')
    if isinstance(nested_keys, list):
        cleaned['keys'] = [strip_private_key_material(k) for k in nested_keys]
    return cleaned

def _key_set_id(key):
    key_set = key.get('set') if isinstance(key, dict) else None
    if isinstance(key_set, dict):
        return key_set.get('id') or key_set.get('name')
    return key_set

def get_keys_and_key_sets(tag, key_set_name=None, base_url=None):
    """
    Return full Kong key and key-set objects tagged for a namespace.

    Private key material is stripped. Optional key_set_name further filters
    to a single key set and its keys.
    """
    keys = recurse_get_records(
        [], "/keys?tags=%s" % quote(tag), base_url=base_url
    )
    key_sets = recurse_get_records(
        [], "/key-sets?tags=%s" % quote(tag), base_url=base_url
    )

    if key_set_name:
        key_sets = [
            ks for ks in key_sets if ks.get('name') == key_set_name
        ]
        allowed_ids = {
            ks.get('id') for ks in key_sets if ks.get('id')
        }
        allowed_ids.add(key_set_name)
        keys = [k for k in keys if _key_set_id(k) in allowed_ids]

    return {
        "key_sets": [strip_private_key_material(ks) for ks in key_sets],
        "keys": [strip_private_key_material(k) for k in keys],
    }

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

def recurse_get_records (result, url, base_url = None):
    log = app.logger
    if base_url is None:
        admin_url = app.config['kongAdminUrl']
    else:
        admin_url = base_url

    log.debug("%s%s" % (admin_url, url))
    r = requests.get("%s%s" % (admin_url, url))
    json =  r.json()
    data = json['data']
    result.extend(data)

    if json['next'] is not None:
        recurse_get_records (result, json['next'], base_url=admin_url)
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