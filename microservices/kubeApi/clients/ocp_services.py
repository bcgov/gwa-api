# Build a Kubernetes yaml file of all the services based on the
# kong-specs configuration
from fastapi import HTTPException
import json
import time
from datetime import datetime
from subprocess import Popen, PIPE, STDOUT
from templates.services import SERVICE, SERVICE_HEAD
from config import settings
from fastapi.logger import logger
from clients.ocp_routes import kubectl_apply

def apply_services(rootPath):
    kubectl_apply("%s/services-current.yaml" % rootPath)

def delete_services(rootPath):
    print(rootPath)
    args = [
        "kubectl", "delete", "-f", "%s/services-deletions.yaml" % rootPath
    ]
    run = Popen(args, stdout=PIPE, stderr=STDOUT)
    out, err = run.communicate()
    if run.returncode != 0:
        logger.error("Failed to delete services", out, err)
        raise Exception("Failed to delete services")

def prepare_mismatched_services(select_tag, hosts, rootPath):

    args = [
        "kubectl", "get", "services", "-l", "aps-select-tag=%s" % select_tag, "-o", "json"
    ]
    run = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = run.communicate()
    if run.returncode != 0:
        logger.error("Failed to get existing services", out, err)
        raise Exception("Failed to get existing services")

    current_services = []

    existing = json.loads(out)
    for route in existing['items']:
        current_services.append(route['metadata']['name'])

    delete_list = []
    for service_name in current_services:
        match = False
        for host in hosts:
            name = host.split(".")[0]
            if service_name == name:
                match = True
        if match == False:
            delete_list.append(service_name)

    out_filename = "%s/services-deletions.yaml" % rootPath

    with open(out_filename, 'w') as out_file:
        index = 1
        for service_name in delete_list:
            logger.debug("[%s] Service D %03d %s" % (select_tag, index, service_name))
            out_file.write(SERVICE_HEAD.substitute(name=service_name))
            out_file.write('\n---\n')
            index = index + 1

    if len(delete_list) == 0:
        logger.debug("[%s] Service D No Deletions Needed" % select_tag)

    return len(delete_list)


def prepare_service_last_version(ns, select_tag):
    args = [
        "kubectl", "get", "services", "-l", "aps-select-tag=%s" % select_tag, "-o", "json"
    ]
    run = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = run.communicate()
    if run.returncode != 0:
        logger.error("Failed to get existing services", out, err)
        raise Exception("Failed to get existing services")

    resource_versions = {}

    existing = json.loads(out)
    for service in existing['items']:
        resource_versions[service['metadata']['name']] = service['metadata']['resourceVersion']
    return resource_versions


def prepare_apply_services(ns, select_tag, hosts, rootPath, data_plane):
    out_filename = "%s/services-current.yaml" % rootPath
    ts = int(time.time())
    fmt_time = datetime.now().strftime("%Y.%m-%b.%d")

    resource_versions = prepare_service_last_version(ns, select_tag)

    with open(out_filename, 'w') as out_file:
        index = 1
        for host in hosts:
            name = host.split(".")[0]

            resource_version = ""
            if name in resource_versions:
                resource_version = resource_versions[name]

            secret_name = gen_secret_name_from_service_name(name)
            
            logger.debug("[%s] Service A %03d %s (ver.%s)" %
                         (select_tag, index, host, resource_version))
            out_file.write(SERVICE.substitute(name=name, ns=ns, select_tag=select_tag, resource_version=resource_version,
                                            secret_name=secret_name,
                                            service_name=data_plane, timestamp=ts, fmt_time=fmt_time, data_plane=data_plane))
            out_file.write('\n---\n')
            index = index + 1
        out_file.close()
    return len(hosts)


def get_gwa_ocp_services(extralabels=""):

    label = "aps-generated-by=gwa-cli"
    if not extralabels == None and not extralabels == "":
        label = label + "," + extralabels
    args = [
        "kubectl", "get", "services", "-l", label, "-o", "json"
    ]
    run = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = run.communicate()

    if run.returncode != 0:
        logger.error("Failed to get existing services", out, err)
        raise Exception("Failed to get existing services")

    return json.loads(out)['items']

def get_gwa_ocp_service_secrets(extralabels=""):

    secret_names = []
    result_data = []
    services = get_gwa_ocp_services(extralabels=extralabels)
    for service in services:
      secret_name = gen_secret_name_from_service_name(service['metadata']['name'])
      result_data.append({
        "host": "%s.%s.svc.cluster.local" % (service['metadata']['name'], service['metadata']['namespace']),
        "secret_name": secret_name
      })
      secret_names.append(secret_name)

    try_secret_fetch(1, secret_names, result_data)

    return result_data

def try_secret_fetch (tries, secret_names, result_data):
    try:
      secret_data = get_secrets(secret_names)
      
      for secret in result_data:
        secret['data'] = get_secret_data(secret['secret_name'], secret_data)

    except Exception as ex:
      tries = tries + 1
      if tries == 4:
        logger.error("[secret_fetch] Too many attempts to fetch secret")
        raise Exception ("Service Serving Certs missing")

      logger.info("[secret_fetch] Try # %d" % tries)
      return try_secret_fetch (tries + 1, secret_names, result_data)

def get_secrets(names):
    args = [
        "kubectl", "get", "-o", "json"
    ]
    for name in names:
      args.append("secret/%s" % name)
    
    logger.debug("[get_secrets] %s" % args)

    run = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = run.communicate()

    if run.returncode != 0:
        logger.error("Failed to get existing secrets", out, err)
        raise Exception("Failed to get existing secrets")

    json_out = json.loads(out)
    if 'items' in json_out:
        return json_out['items']
    else:
        return [ json_out ]

def gen_secret_name_from_service_name (name: str):
    return "%s-service-ssl" % name
  
def get_secret_data (name, secret_data):
    for secret in secret_data:
        if secret['metadata']['name'] == name:
            return secret
    raise Exception ("Missing secret %s" % name)
