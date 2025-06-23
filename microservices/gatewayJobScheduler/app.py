import os
import logging
import traceback
from clients.namespace import NamespaceService
from cryptography import x509
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

def _format_pem_data(pem_string, indent=8):
    """Format PEM data with proper line breaks and indentation"""
    lines = pem_string.split('\n')
    formatted_lines = [' ' * indent + line for line in lines if line]
    return '\n'.join(formatted_lines)

def _get_select_tag(tags):
    """Extract the namespace select tag from route tags"""
    required_tag = None
    for tag in tags:
        if tag.startswith("ns."):
            required_tag = tag
            if len(tag.split(".")) > 2:
                required_tag = tag
                break
    return required_tag

def _is_host_custom_domain(host):
    """Check if the host is a custom domain"""
    non_custom_suffixes = [
        '.cluster.local', 
        '.api.gov.bc.ca', 
        '.data.gov.bc.ca', 
        '.maps.gov.bc.ca', 
        '.openmaps.gov.bc.ca',
        '.apps.gov.bc.ca',
        '.apis.gov.bc.ca',
        '.test'
    ]
    
    for suffix in non_custom_suffixes:
        if host == suffix[1:] or host.endswith(suffix):
            return False

    return True

def _get_certificate_for_host(host, namespace, cert_snis, certs):
    """
    Find and return certificate details for a given host
    Returns: tuple (cert, serial_number)
    """
    cert = None
    serial_number = None
    
    if not _is_host_custom_domain(host):
        return cert, serial_number
        
    logger.debug("%s - Searching for custom cert for %s" % (namespace, host))
    if not cert_snis:
        raise Exception(f"Certificate SNI not found for host {host}")
        
    for sni in cert_snis:
        if host in sni['name']:
            cert_id = sni['certificate']['id']
            logger.debug("%s - Found custom cert with SNI match for %s - %s" % (namespace, host, cert_id))
            cert = next((cert for cert in certs if cert['id'] == cert_id), None)
            if cert is None:
                raise Exception("Certificate not found for id %s" % cert_id)
                
            try:
                # Format and parse the PEM certificate
                formatted_cert = _format_pem_data(cert['cert'])
                x509_cert = x509.load_pem_x509_certificate(
                    formatted_cert.encode(),
                    default_backend()
                )
                # Get serial number as integer and convert to hex string
                serial_number = format(x509_cert.serial_number, 'x')
                
                cert['snis'] = [host]
                return cert, serial_number
            except Exception as e:
                logger.error(f"Error decoding certificate: {str(e)}")
                raise Exception(f"Failed to decode certificate for host {host}: {str(e)}")
            
    raise Exception("Certificate not found for host %s" % host)

def transform_data_by_ns(routes, certs, cert_snis):
    """Transform route data organized by namespace"""
    ns_svc = NamespaceService()
    try:
        ns_dict = {}
        ns_attr_dict = {}
        for route_obj in routes:
            select_tag = _get_select_tag(route_obj['tags'])
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
                    # Look for a matching certificate by SNI for custom domainsAdd commentMore actions
                    cert, serial_number = _get_certificate_for_host(host, namespace, cert_snis, certs)

                    name = 'wild-%s-%s' % (select_tag.replace(".", "-"), host)
                    ns_dict[namespace].append({
                        "name": name,
                        "selectTag": select_tag,
                        "host": host,
                        "sessionCookieEnabled": session_cookie_enabled,
                        "dataClass": data_class,
                        "dataPlane": os.getenv('DATA_PLANE'),
                        "sslCertificateSerialNumber": serial_number,
                        "certificates": [cert] if cert is not None else None
                    })
        return ns_dict
    except Exception as err:
        traceback.print_exc()
        logger.error("Error transforming data. %s" % str(err))