# Build a Kubernetes yaml file of all the routes based on the 
# kong-specs configuration
import os
import yaml
import time
from datetime import datetime
from subprocess import Popen, PIPE, STDOUT
from flask import current_app as app
from string import Template

def apply_routes (rootPath):
    log = app.logger
    args = [
        "kubectl", "apply", "-f", "%s/routes.yaml" % rootPath
    ]
    run = Popen(args, stdout=PIPE, stderr=STDOUT)
    out, err = run.communicate()
    if run.returncode != 0:
        log.error("Failed to apply routes", out, err)
        raise Exception("Failed to apply routes")

def prepare_routes (ns, rootPath):
    ssl_key_path = "/ssl/tls.key"
    ssl_crt_path = "/ssl/tls.crt"

    files_to_ignore = ["deck.yaml", "routes.yaml"]

    host_list = []

    out_filename = "%s/routes.yaml" % rootPath

    def read_and_indent(full_path, indent):
        pad = "                    "
        stream = open(full_path, 'r')
        lines = stream.readlines()
        result = ""
        for line in lines:
            result = "%s%s%s" % (result, pad[:indent], line)
        return result

    for x in os.walk(rootPath):
        for file in x[2]:
            if file not in files_to_ignore:
                full_path = "%s/%s" % (x[0],file)

                stream = open(full_path, 'r')
                data = yaml.load(stream)
                # yaml.load(input, Loader=yaml.SafeLoader)

                if 'services' in data:
                    for service in data['services']:
                        if 'routes' in service:
                            for route in service['routes']:
                                if 'hosts' in route:
                                    for host in route['hosts']:
                                        if host not in host_list:
                                            host_list.append(host)

    host_list.sort()


    template = Template("""
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ${name}
  annotations:
  labels:
    aps-generated-by: "gwa-cli"
    aps-published-on: "${fmt_time}"
    aps-namespace: "${ns}"
    aps-published-ts: "${timestamp}"
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
    fmt_time = datetime.now().strftime("%Y/%m-%b/%d")

    ssl_key = read_and_indent(ssl_key_path, 8)
    ssl_crt = read_and_indent(ssl_crt_path, 8)

    with open(out_filename, 'w') as out_file:
        index = 1
        for host in host_list:
            print("Route %03d %s" % (index, host))
            out_file.write(template.substitute(name="wild-%s" % host, ns=ns, host=host, path='/', ssl_key=ssl_key, ssl_crt=ssl_crt, serviceName='kong-dev-kong-proxy', timestamp=ts, fmt_time=fmt_time))
            out_file.write('\n---\n')
            index = index + 1

