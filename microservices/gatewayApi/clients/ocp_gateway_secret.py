import yaml
from flask import current_app as app
import base64
import time
from datetime import datetime
from clients.ocp_routes import kubectl_apply, files_to_ignore
from string import Template

def prep_submitted_config (docs):
    content = []
    for gw_config in docs:
        content.append(yaml.dump(gw_config))
    file_content = "\n---\n".join(content)

    return file_content
 
def write_submitted_config (file_content, rootPath):
    out_filename = "%s/submitted_config.txt" % rootPath

    with open(out_filename, 'w') as out_file:
        out_file.write(file_content)

def prep_and_apply_secret (ns, select_tag, rootPath):
    out_filename = "%s/submitted_config_secret.yaml" % rootPath

    template = Template("""
apiVersion: v1
kind: Secret
type: Opaque
metadata:
  name: ${name}
  annotations:
  labels:
    aps-generated-by: "gwa-cli"
    aps-published-on: "${fmt_time}"
    aps-namespace: "${ns}"
    aps-select-tag: "${select_tag}"
    aps-published-ts: "${timestamp}"
data:
  config: "${config}"
""")

    ts = int(time.time())
    fmt_time = datetime.now().strftime("%Y.%m-%b.%d")

    with open("%s/submitted_config.txt" % rootPath, 'r') as in_file:
        config = base64.b64encode(in_file.read().encode('utf-8')).decode('utf-8')

    with open(out_filename, 'w') as out_file:
        out_file.write(template.substitute(name="gwa-orig-%s" % (select_tag.replace('.','-')), ns=ns, select_tag=select_tag, config=config, timestamp=ts, fmt_time=fmt_time))
        out_file.write('\n---\n')

    kubectl_apply (out_filename)

