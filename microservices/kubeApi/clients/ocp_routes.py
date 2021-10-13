# Build a Kubernetes yaml file of all the routes based on the
# kong-specs configuration
from fastapi.logger import logger
from fastapi import HTTPException
import os
import json
import yaml
import time
from datetime import datetime
from subprocess import Popen, PIPE, STDOUT
from templates.routes import ROUTE, ROUTE_HEAD
from config import settings

files_to_ignore = ["deck.yaml", "routes-current.yaml", "routes-deletions.yaml",
                   "submitted_config.yaml", "submitted_config_secret.yaml"]

host_cert_mapping = {
    "data.gov.bc.ca": "data-api.tls",
    "api.gov.bc.ca": "data-api.tls",
    "apps.gov.bc.ca": "apps.tls"
}


def read_and_indent(full_path, indent):
    pad = "                    "
    stream = open(full_path, 'r')
    lines = stream.readlines()
    result = ""
    for line in lines:
        result = "%s%s%s" % (result, pad[:indent], line)
    return result


def apply_routes(rootPath):
    kubectl_apply("%s/routes-current.yaml" % rootPath)


def kubectl_apply(fileName):
    args = [
        "kubectl", "apply", "-f", fileName
    ]
    run = Popen(args, stdout=PIPE, stderr=STDOUT)
    out, err = run.communicate()
    if run.returncode != 0:
        logger.error("Failed to apply", out, err)
        raise HTTPException(status_code=400, detail="Failed to apply routes")


def kubectl_delete(type, name):
    args = [
        "kubectl", "delete", type, name
    ]
    run = Popen(args, stdout=PIPE, stderr=STDOUT)
    out, err = run.communicate()
    if run.returncode != 0:
        logger.error("Failed to delete", out, err)
        raise HTTPException(status_code=400, detail="Failed to delete %s %s" % (type, name))


def delete_routes(rootPath):
    print(rootPath)
    args = [
        "kubectl", "delete", "-f", "%s/routes-deletions.yaml" % rootPath
    ]
    run = Popen(args, stdout=PIPE, stderr=STDOUT)
    out, err = run.communicate()
    if run.returncode != 0:
        logger.error("Failed to delete routes", out, err)
        raise Exception("Failed to delete routes")


def prepare_mismatched_routes(select_tag, hosts, rootPath):

    args = [
        "kubectl", "get", "routes", "-l", "aps-select-tag=%s" % select_tag, "-o", "json"
    ]
    run = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = run.communicate()
    if run.returncode != 0:
        logger.error("Failed to get existing routes", out, err)
        raise Exception("Failed to get existing routes")

    current_routes = []

    existing = json.loads(out)
    for route in existing['items']:
        current_routes.append(route['metadata']['name'])
    print(str(current_routes))
    delete_list = []
    for route_name in current_routes:
        match = False
        for host in hosts:
            if route_name == "wild-%s-%s" % (select_tag.replace('.', '-'), host):
                match = True
        if match == False:
            delete_list.append(route_name)

    out_filename = "%s/routes-deletions.yaml" % rootPath

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
        logger.error("Failed to get existing routes", out, err)
        raise Exception("Failed to get existing routes")

    resource_versions = {}

    existing = json.loads(out)
    for route in existing['items']:
        resource_versions[route['metadata']['name']] = route['metadata']['resourceVersion']
    return resource_versions


def prepare_apply_routes(ns, select_tag, hosts, rootPath):
    out_filename = "%s/routes-current.yaml" % rootPath
    ts = int(time.time())
    fmt_time = datetime.now().strftime("%Y.%m-%b.%d")

    resource_versions = prepare_route_last_version(ns, select_tag)

    with open(out_filename, 'w') as out_file:
        index = 1
        for host in hosts:
            # If host transformation is disabled, then select the appropriate
            # SSL cert based on the suffix mapping
            ssl_ref = "tls"
            if not settings.hostTransformation['enabled']:
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
            out_file.write(ROUTE.substitute(name=name, ns=ns, select_tag=select_tag, resource_version=resource_version, host=host, path='/',
                                            ssl_ref=ssl_ref, ssl_key=ssl_key, ssl_crt=ssl_crt, service_name=settings.dataPlane, timestamp=ts, fmt_time=fmt_time))
            out_file.write('\n---\n')
            index = index + 1
    return len(hosts)


def get_host_list(rootPath):
    host_list = []

    for x in os.walk(rootPath):
        for file in x[2]:
            if file not in files_to_ignore:
                full_path = "%s/%s" % (x[0], file)

                stream = open(full_path, 'r')
                data = yaml.load(stream, Loader=yaml.SafeLoader)

                if data is not None and 'services' in data:
                    for service in data['services']:
                        if 'routes' in service:
                            for route in service['routes']:
                                if 'hosts' in route:
                                    for host in route['hosts']:
                                        if host not in host_list:
                                            host_list.append(host)

    host_list.sort()
    return host_list


def get_gwa_ocp_routes():
    args = [
        "kubectl", "get", "routes", "-l", "aps-generated-by=gwa-cli", "-o", "json"
    ]
    run = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = run.communicate()

    if run.returncode != 0:
        logger.error("Failed to get existing routes", out, err)
        raise Exception("Failed to get existing routes")

    return json.loads(out)['items']
