import os
import logging
import traceback
from clients.namespace import NamespaceService
import traceback

logger = logging.getLogger(__name__)

def transform_data_by_ns(routes, certs):
    ns_svc = NamespaceService()
    try:
        ns_dict = {}
        ns_attr_dict = {}
        for route_obj in routes:
            select_tag = get_select_tag(route_obj['tags'])
            namespace = select_tag.split(".")[1]

            if namespace not in ns_dict:
                ns_dict[namespace] = []
                ns_attr_dict[namespace] = ns_svc.get_namespace_attributes(namespace)

            logger.debug("%s - %s" % (namespace, ns_attr_dict[namespace].get('perm-data-plane', [''])))

            # check if namespace has data plane attribute and needs to be synced
            if ns_attr_dict[namespace].get('perm-data-plane', [''])[0] == os.getenv('DATA_PLANE'):
                # extract override values
                session_cookie_enabled = False
                if 'aps.route.session.cookie.enabled' in route_obj['tags']:
                    session_cookie_enabled = True
                data_class = None
                for tag in route_obj['tags']:
                    if tag.startswith('aps.route.dataclass'):
                        data_class = tag.split(".")[-1]
                        break

                for host in route_obj['hosts']:
                    # Look for a matching certificate by SNI for custom domains
                    cert_id = None
                    custom_cert_found = False
                    if is_host_custom_domain(host):
                        logger.debug("%s - Searching for custom cert for %s" % (namespace, host))
                        if certs:
                            for cert in certs:
                                if host in cert['snis']:
                                    cert_id = cert['id']
                                    logger.debug("%s - Found custom cert with SNI match for %s - %s" % (namespace, host, cert_id))
                                    custom_cert_found = True
                                    break
                            if not custom_cert_found:
                                raise Exception("Custom certificate not found for host %s" % host)
                            
                    name = 'wild-%s-%s' % (select_tag.replace(".", "-"), host)
                    ns_dict[namespace].append({"name": name, "selectTag": select_tag, "host": host,
                                               "sessionCookieEnabled": session_cookie_enabled,
                                               "dataClass": data_class,
                                               "dataPlane": os.getenv('DATA_PLANE'),
                                               "customCertificateId": cert_id})
        return ns_dict
    except Exception as err:
        traceback.print_exc()
        logger.error("Error transforming data. %s" % str(err))

def get_select_tag(tags):
    required_tag = None
    for tag in tags:
        if tag.startswith("ns."):
            required_tag = tag
            if len(tag.split(".")) > 2:
                required_tag = tag
                break
    return required_tag

def is_host_custom_domain(host):
    non_custom_suffixes = [
        '.cluster.local', 
        '.api.gov.bc.ca', 
        '.data.gov.bc.ca', 
        '.maps.gov.bc.ca', 
        '.openmaps.gov.bc.ca',
        '.apps.gov.bc.ca',
        '.apis.gov.bc.ca'
    ]
    
    # Check if the host is one of the standard cert domains or a subdomain of them
    for suffix in non_custom_suffixes:
        if host == suffix[1:] or host.endswith(suffix):
            return False

    return True