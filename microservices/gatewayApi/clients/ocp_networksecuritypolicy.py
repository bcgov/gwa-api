import time
import os
import yaml
from datetime import datetime
from flask import current_app as app
from string import Template
from subprocess import Popen, PIPE, STDOUT

from clients.ocp_routes import kubectl_apply, kubectl_delete, files_to_ignore

def check_nsp (ns, ocp_ns):
    log = app.logger
    b = check_exists ("nsp", ns, ocp_ns)
    log.debug("[%s] Check? aps-upstream-%s-%s : %s" % (ns, ns, ocp_ns, b))
    return b

    
def check_exists (_type, ns, ocp_ns):
    log = app.logger
    args = [
        "kubectl", "get", _type, "aps-upstream-%s-%s" % (ns, ocp_ns)
    ]
    run = Popen(args, stdout=PIPE, stderr=STDOUT)
    out, err = run.communicate()
    if run.returncode != 0:
        return False
    else:
        return True

def apply_nsp (ns, ocp_ns, rootPath):
    log = app.logger

    template = Template("""
kind: NetworkSecurityPolicy
apiVersion: security.devops.gov.bc.ca/v1alpha1
metadata:
  name: aps-upstream-${ns}-${ocp_ns}
  labels:
    aps-generated-by: "gwa-cli"
    aps-published-on: "${fmt_time}"
    aps-namespace: "${ns}"
    aps-published-ts: "${timestamp}"
spec:
  description: |
    allow namespace to access the internet
  source:
    - - app.kubernetes.io/instance=kong
  destination:
    - - $$namespace=${ocp_ns}
""")

    ts = int(time.time())
    fmt_time = datetime.now().strftime("%Y.%m-%b.%d")

    out_filename = "%s/nsp.yaml" % rootPath

    with open(out_filename, 'w') as out_file:
        index = 1
        log.debug("[%s] NSP aps-upstream-%s-%s" % (ns, ns, ocp_ns))
        out_file.write(template.substitute(ns=ns, ocp_ns=ocp_ns, timestamp=ts, fmt_time=fmt_time))
        out_file.write('\n---\n')
        index = index + 1

    kubectl_apply (out_filename)

def delete_nsp (ns, ocp_ns):
    log = app.logger

    name = "aps-upstream-%s-%s" % (ns, ocp_ns)
    
    kubectl_delete ("nsp", name)

def get_ocp_service_namespaces(rootPath):
    service_ns_list = []

    for x in os.walk(rootPath):
        for file in x[2]:
            if file not in files_to_ignore:
                full_path = "%s/%s" % (x[0],file)

                stream = open(full_path, 'r')
                data = yaml.load(stream, Loader=yaml.SafeLoader)

                if 'services' in data:
                    for service in data['services']:
                        if 'host' in service and service['host'].endswith('.svc'):
                            h = service['host']
                            parts = h.split('.')
                            ns = parts[len(parts) - 2]
                            service_ns_list.append(ns)

    service_ns_list = list(set(service_ns_list))
    return service_ns_list

# def prepare_deletions (ns, ocp_ns, rootPath):
#     log = app.logger

#     args = [
#         "kubectl", "get", "nsp", "-l", "aps-namespace=%s" % select_tag, "-o", "json"
#     ]
#     run = Popen(args, stdout=PIPE, stderr=PIPE)
#     out, err = run.communicate()
#     if run.returncode != 0:
#         log.error("Failed to get existing routes", out, err)
#         raise Exception("Failed to get existing routes")

#     current_routes = []

#     existing = json.loads(out)
#     for route in existing['items']:
#         current_routes.append(route['metadata']['name'])

#     host_list = get_host_list(rootPath)

#     delete_list = []
#     for route_name in current_routes:
#         match = False
#         for host in host_list:
#             if route_name == "wild-%s-%s" % (select_tag.replace('.','-'), host):
#                 match = True
#         if match == False:
#             delete_list.append(route_name)

#     template = Template("""
# apiVersion: route.openshift.io/v1
# kind: Route
# metadata:
#   name: ${name}

# """)

#     ts = int(time.time())
#     fmt_time = datetime.now().strftime("%Y.%m-%b.%d")

#     out_filename = "%s/routes-deletions.yaml" % rootPath

#     with open(out_filename, 'w') as out_file:
#         index = 1
#         for route_name in delete_list:
#             log.debug("[%s] Route D %03d %s" % (select_tag, index, route_name))
#             out_file.write(template.substitute(name=route_name))
#             out_file.write('\n---\n')
#             index = index + 1

#     if len(delete_list) == 0:
#         log.debug("[%s] Route D No Deletions Needed" % select_tag)

#     return len(delete_list)