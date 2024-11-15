# Build a Kubernetes yaml file of all the routes based on the
# kong-specs configuration
from fastapi import HTTPException
import json
import time
from datetime import datetime
from subprocess import Popen, PIPE, STDOUT
from templates.v1.routes import ROUTE, ROUTE_HEAD
from templates.v2.routes import V2_ROUTE
from config import settings
from fastapi.logger import logger

files_to_ignore = ["deck.yaml", "routes-current.yaml", "routes-deletions.yaml",
                   "submitted_config.yaml", "submitted_config_secret.yaml"]

host_cert_mapping = {
    "data.gov.bc.ca": "data-api.tls",
    "api.gov.bc.ca": "data-api.tls",
    "apps.gov.bc.ca": "apps.tls"
}

ROUTES = {
    "v1": {
        "ROUTE": ROUTE
    },
    "v2": {
        "ROUTE": V2_ROUTE
    }
}

data_class_mapping = {
    'aps.route.dataclass.low': 'low',
    'aps.route.dataclass.medium': 'medium',
    'aps.route.dataclass.high': 'high',
    'aps.route.dataclass.public': 'public'
}

def read_and_indent(full_path, indent):
    pad = "                    "
    stream = open(full_path, 'r')
    lines = stream.readlines()
    result = ""
    for line in lines:
        result = "%s%s%s" % (result, pad[:indent], line)
    return result

def format_pem_data(pem_string, indent=8):
    """Format PEM data with proper line breaks and indentation"""
    lines = pem_string.split('\n')
    formatted_lines = [' ' * indent + line for line in lines if line]
    return '\n'.join(formatted_lines)


def apply_routes(root_path):
    kubectl_apply("%s/routes-current.yaml" % root_path)


def kubectl_apply(file_name):
    args = [
        "kubectl", "apply", "-f", file_name
    ]
    run = Popen(args, stdout=PIPE, stderr=STDOUT)

    out, err = run.communicate()
    if run.returncode != 0:
        ERR_MSG="Failed to apply routes"
        logger.error("%s : %s %s" % (ERR_MSG, out, err))
        raise HTTPException(status_code=400, detail=ERR_MSG)


def kubectl_delete(type, name):
    args = [
        "kubectl", "delete", type, name
    ]
    run = Popen(args, stdout=PIPE, stderr=STDOUT)
    out, err = run.communicate()
    if run.returncode != 0:
        ERR_MSG="Failed to delete %s %s" % (type, name)
        logger.error("%s : %s %s" % (ERR_MSG, out, err))
        raise HTTPException(status_code=400, detail=ERR_MSG)


def delete_routes(root_path):
    args = [
        "kubectl", "delete", "-f", "%s/routes-deletions.yaml" % root_path
    ]
    run = Popen(args, stdout=PIPE, stderr=STDOUT)
    out, err = run.communicate()
    if run.returncode != 0:
        ERR_MSG="Failed to delete routes"
        logger.error("%s : %s %s" % (ERR_MSG, out, err))
        raise Exception(ERR_MSG)

def prepare_mismatched_routes(select_tag, hosts, root_path):

    args = [
        "kubectl", "get", "routes", "-l", "aps-select-tag=%s" % select_tag, "-o", "json"
    ]
    run = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = run.communicate()
    if run.returncode != 0:
        ERR_MSG="Failed to get existing routes"
        logger.error("%s : %s %s" % (ERR_MSG, out, err))
        raise Exception(ERR_MSG)

    current_routes = []

    existing = json.loads(out)
    for route in existing['items']:
        current_routes.append(route['metadata']['name'])

    delete_list = []
    for route_name in current_routes:
        match = False
        for host in hosts:
            if route_name == "wild-%s-%s" % (select_tag.replace('.', '-'), host):
                match = True
        if match == False:
            delete_list.append(route_name)

    out_filename = "%s/routes-deletions.yaml" % root_path

    with open(out_filename, 'w') as out_file:
        index = 1
        for route_name in delete_list:
            logger.debug("[%s] Route D %03d %s" % (select_tag, index, route_name))
            out_file.write(ROUTE_HEAD.substitute(name=route_name))
            out_file.write('\n---\n')
            index = index + 1

    if len(delete_list) == 0:
        logger.debug("[%s] Route D No Deletions Needed" % select_tag)

    return len(delete_list)


def prepare_route_last_version(ns, select_tag):
    args = [
        "kubectl", "get", "routes", "-l", "aps-select-tag=%s" % select_tag, "-o", "json"
    ]
    run = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = run.communicate()
    if run.returncode != 0:
        ERR_MSG="Failed to get existing routes"
        logger.error("%s : %s %s" % (ERR_MSG, out, err))
        raise Exception(ERR_MSG)

    resource_versions = {}

    existing = json.loads(out)
    for route in existing['items']:
        resource_versions[route['metadata']['name']] = route['metadata']['resourceVersion']
    return resource_versions


def prepare_apply_routes(ns, select_tag, hosts, root_path, data_plane, ns_template_version, overrides, certificates=None):
    out_filename = "%s/routes-current.yaml" % root_path
    ts = time_secs()
    fmt_time = datetime.fromtimestamp(ts).strftime("%Y.%m-%b.%d")

    resource_versions = prepare_route_last_version(ns, select_tag)

    with open(out_filename, 'w') as out_file:
        index = 1
        for host in hosts:
            data_class_annotation = ''
            templ_version = ns_template_version
            if overrides:
                if 'aps.route.session.cookie.enabled' in overrides and host in overrides['aps.route.session.cookie.enabled']:
                    templ_version = 'v1'
                    logger.debug("[%s] %s Template version override applied %s", select_tag, host, templ_version)

                for tag, value in data_class_mapping.items():
                    if overrides.get(tag) and host in overrides[tag]:
                        data_class = value
                        data_class_annotation = f'    aviinfrasetting.ako.vmware.com/name: "dataclass-{value}"'
                        logger.debug("[%s] %s Dataclass override applied %s -> %s", select_tag, host, tag, data_class)
            else:
                logger.debug("[%s] %s No override applied %s", select_tag, hosts, str(overrides))

            route_template = ROUTES[templ_version]["ROUTE"]

            # Modified certificate selection logic
            ssl_ref = "tls"
            cert_id = ''
            custom_cert_found = False
            
            if is_host_custom_domain(host):
                logger.debug("[%s] Route A %03d Searching for custom cert for %s" % (select_tag, index, host))
                if certificates:
                    # Look for a matching certificate by SNI
                    for cert in certificates:
                        if host in cert['snis']:
                            ssl_key = format_pem_data(cert['key'])
                            ssl_crt = format_pem_data(cert['cert'])
                            cert_id = cert['id']
                            custom_cert_label = f'    aps-certificate-id: "{cert_id}"'
                            logger.debug("[%s] Route A %03d Found custom cert with SNI match for %s" % (select_tag, index, host))
                            custom_cert_found = True
                            break
                    if not custom_cert_found:
                        raise Exception("Custom certificate not found for host %s" % host)
                
            if not custom_cert_found and not settings.host_transformation['enabled']:
                # Fall back to existing cert mapping logic
                for host_match, ssl_file_prefix in host_cert_mapping.items():
                    if host.endswith(host_match):
                        ssl_ref = ssl_file_prefix
                        logger.debug("[%s] Route A %03d matched ssl cert %s" % (select_tag, index, ssl_ref))
                ssl_key = read_and_indent("/ssl/%s.key" % ssl_ref, 8)
                ssl_crt = read_and_indent("/ssl/%s.crt" % ssl_ref, 8)

            name = "wild-%s-%s" % (select_tag.replace('.', '-'), host)

            resource_version = ""
            if name in resource_versions:
                resource_version = resource_versions[name]

            logger.debug("[%s] Route A %03d wild-%s-%s (ver.%s)" %
                         (select_tag, index, select_tag.replace('.', '-'), host, resource_version))
            out_file.write(route_template.substitute(name=name, ns=ns, select_tag=select_tag, resource_version=resource_version, host=host, path='/',
                                            ssl_ref=ssl_ref, ssl_key=ssl_key, ssl_crt=ssl_crt, service_name=data_plane, timestamp=ts, fmt_time=fmt_time, data_plane=data_plane,
                                            data_class_annotation=data_class_annotation, template_version=templ_version, custom_cert_label=custom_cert_label))
            out_file.write('\n---\n')
            index = index + 1
        out_file.close()
    return len(hosts)


def get_gwa_ocp_routes(extralabels=""):

    label = "aps-generated-by=gwa-cli"
    if not extralabels == None and not extralabels == "":
        label = label + "," + extralabels
    args = [
        "kubectl", "get", "routes", "-l", label, "-o", "json"
    ]
    run = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = run.communicate()

    if run.returncode != 0:
        ERR_MSG="Failed to get existing routes"
        logger.error("%s : %s %s" % (ERR_MSG, out, err))
        raise Exception(ERR_MSG)

    return json.loads(out)['items']

def time_secs():
    return int(time.time())

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