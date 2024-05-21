# Build a Kubernetes yaml file of all the routes based on the 
# kong-specs configuration
import os
import json
import yaml
import time
from datetime import datetime
from subprocess import Popen, PIPE, STDOUT
from flask import current_app as app
from string import Template

files_to_ignore = ["deck.yaml", "routes-current.yaml", "routes-deletions.yaml", "submitted_config.yaml", "submitted_config_secret.yaml"]

host_cert_mapping = {
    "data.gov.bc.ca" : "data-api.tls",
    "api.gov.bc.ca" : "data-api.tls",
    "apps.gov.bc.ca" : "apps.tls"
}

def read_and_indent(full_path, indent):
    pad = "                    "
    stream = open(full_path, 'r')
    lines = stream.readlines()
    result = ""
    for line in lines:
        result = "%s%s%s" % (result, pad[:indent], line)
    return result

def apply_routes (rootPath):
    kubectl_apply ("%s/routes-current.yaml" % rootPath)

def kubectl_apply (fileName):
    log = app.logger
    args = [
        "kubectl", "apply", "-f", fileName
    ]
    run = Popen(args, stdout=PIPE, stderr=STDOUT)
    out, err = run.communicate()
    if run.returncode != 0:
        log.error("Failed to apply", out, err)
        raise Exception("Failed to apply routes")

def kubectl_delete (type, name):
    log = app.logger
    args = [
        "kubectl", "delete", type, name
    ]
    run = Popen(args, stdout=PIPE, stderr=STDOUT)
    out, err = run.communicate()
    if run.returncode != 0:
        log.error("Failed to delete", out, err)
        raise Exception("Failed to apply routes")

def delete_routes (rootPath):
    log = app.logger
    args = [
        "kubectl", "delete", "-f", "%s/routes-deletions.yaml" % rootPath
    ]
    run = Popen(args, stdout=PIPE, stderr=STDOUT)
    out, err = run.communicate()
    if run.returncode != 0:
        log.error("Failed to delete routes", out, err)
        raise Exception("Failed to delete routes")

def prepare_delete_routes (ns, select_tag, rootPath):
    log = app.logger

    args = [
        "kubectl", "get", "routes", "-l", "aps-select-tag=%s" % select_tag, "-o", "json"
    ]
    run = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = run.communicate()
    if run.returncode != 0:
        log.error("Failed to get existing routes", out, err)
        raise Exception("Failed to get existing routes")

    current_routes = []

    existing = json.loads(out)
    for route in existing['items']:
        current_routes.append(route['metadata']['name'])

    host_list = get_host_list(rootPath)

    delete_list = []
    for route_name in current_routes:
        match = False
        for host in host_list:
            if route_name == "wild-%s-%s" % (select_tag.replace('.','-'), host):
                match = True
        if match == False:
            delete_list.append(route_name)

    template = Template("""
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ${name}

""")

    ts = int(time.time())
    fmt_time = datetime.now().strftime("%Y.%m-%b.%d")

    out_filename = "%s/routes-deletions.yaml" % rootPath

    with open(out_filename, 'w') as out_file:
        index = 1
        for route_name in delete_list:
            log.debug("[%s] Route D %03d %s" % (select_tag, index, route_name))
            out_file.write(template.substitute(name=route_name))
            out_file.write('\n---\n')
            index = index + 1

    if len(delete_list) == 0:
        log.debug("[%s] Route D No Deletions Needed" % select_tag)

    return len(delete_list)

def prepare_route_last_version (ns, select_tag):
    log = app.logger

    args = [
        "kubectl", "get", "routes", "-l", "aps-select-tag=%s" % select_tag, "-o", "json"
    ]
    run = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = run.communicate()
    if run.returncode != 0:
        log.error("Failed to get existing routes", out, err)
        raise Exception("Failed to get existing routes")

    resource_versions = {}

    existing = json.loads(out)
    for route in existing['items']:
        resource_versions[ route['metadata']['name'] ] = route['metadata']['resourceVersion']
    return resource_versions

def prepare_apply_routes (ns, select_tag, is_host_transform_enabled, rootPath):
    log = app.logger
    ssl_key_path = "/ssl/tls.key"
    ssl_crt_path = "/ssl/tls.crt"
    files_to_ignore = ["deck.yaml", "routes.yaml"]

    host_list = get_host_list(rootPath)

    out_filename = "%s/routes-current.yaml" % rootPath

    template = Template("""
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ${name}
  resourceVersion: "${resource_version}"
  annotations:
    haproxy.router.openshift.io/timeout: 30m
  labels:
    aps-generated-by: "gwa-cli"
    aps-published-on: "${fmt_time}"
    aps-namespace: "${ns}"
    aps-select-tag: "${select_tag}"
    aps-published-ts: "${timestamp}"
    aps-ssl: "${ssl_ref}"
spec:
  host: ${host}
  port:
    targetPort: kong-proxy
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
    certificate: |-
${ssl_crt}
    key: |-
${ssl_key}
  to:
    kind: Service
    name: ${serviceName}
    weight: 100
  wildcardPolicy: None
status:
  ingress:
  - host: ${host}
    routerName: router
    wildcardPolicy: None 
""")

    ts = int(time.time())
    fmt_time = datetime.now().strftime("%Y.%m-%b.%d")

    resource_versions = prepare_route_last_version(ns, select_tag)

    with open(out_filename, 'w') as out_file:
        index = 1
        for host in host_list:

            # If host transformation is disabled, then select the appropriate
            # SSL cert based on the suffix mapping
            ssl_ref = "tls"
            if is_host_transform_enabled is False:
                for host_match, ssl_file_prefix in host_cert_mapping.items():
                    if host.endswith(host_match):
                        ssl_ref = ssl_file_prefix
                        log.debug("[%s] Route A %03d matched ssl cert %s" % (select_tag, index, ssl_ref))
            ssl_key = read_and_indent("/ssl/%s.key" % ssl_ref, 8)
            ssl_crt = read_and_indent("/ssl/%s.crt" % ssl_ref, 8)

            name = "wild-%s-%s" % (select_tag.replace('.','-'), host)

            resource_version = ""
            if name in resource_versions:
                resource_version = resource_versions[name]

            log.debug("[%s] Route A %03d wild-%s-%s (ver.%s)" % (select_tag, index, select_tag.replace('.','-'), host, resource_version))
            out_file.write(template.substitute(name=name, ns=ns, select_tag=select_tag, resource_version=resource_version, host=host, path='/', ssl_ref=ssl_ref, ssl_key=ssl_key, ssl_crt=ssl_crt, serviceName='kong-kong-proxy', timestamp=ts, fmt_time=fmt_time))
            out_file.write('\n---\n')
            index = index + 1

    return len(host_list)

def get_host_list(rootPath):

    host_list = []

    for x in os.walk(rootPath):
        for file in x[2]:
            if file not in files_to_ignore:
                full_path = "%s/%s" % (x[0],file)

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


def get_route_overrides(root_path, override_tag):

    host_list = []

    for x in os.walk(root_path):
        for file in x[2]:
            if file not in files_to_ignore:
                full_path = "%s/%s" % (x[0],file)

                stream = open(full_path, 'r')
                data = yaml.load(stream, Loader=yaml.SafeLoader)

                eval_services(host_list, override_tag, data)

    host_list.sort()
    return host_list


def eval_services(host_list, override_tag, data):
    if data is not None and 'services' in data:
        for service in data['services']:
            if 'routes' in service:
                for route in service['routes']:
                    if 'hosts' in route:
                        if override_tag in route['tags']:
                            for host in route['hosts']:
                                if host not in host_list:
                                    host_list.append(host)