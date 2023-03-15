import yaml
from flask import current_app as app
import base64
import time
from datetime import datetime
from clients.ocp_routes import kubectl_apply, files_to_ignore
from string import Template

def prep_submitted_config (docs, masking = True):
    content = []
    for gw_config in docs:
        if gw_config is not None:
            if masking:
                content.append(yaml.dump(mask(gw_config)))
            else:
                content.append(yaml.dump(gw_config))
    file_content = "\n---\n".join(content)

    return file_content
 
def is_blank (obj, key):
    if key not in obj:
        return True
    str = obj[key]
    return str is None or str == ""

def mask_traverse(source, errors, yaml):
    traversables = ['services', 'routes', 'plugins', 'certificates']
    for k in yaml:
        if k in traversables:
            for index, item in enumerate(yaml[k]):
                if k == 'plugins':
                    for maskKey in ['username', 'password', 'secret', 'private_key_location', 'public_key_location', 'client_secret', 'redis_password']:
                        if 'config' in item and not is_blank(item['config'], maskKey):
                            item['config'][maskKey] = '*****'
                if k == 'certificates':
                    if not is_blank(item, 'key'):
                        item['key'] = '*****'
                    if not is_blank(item, 'cert'):
                        item['cert'] = item['cert'][:50] + '...' + item['cert'][-50:].strip()

                nm = "[%d]" % index
                if 'name' in item:
                    nm = item['name']
                mask_traverse("%s.%s.%s" % (source, k, nm), errors, item)


def mask (obj):
    errors = []
    mask_traverse("base", errors, obj)
    return obj

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

