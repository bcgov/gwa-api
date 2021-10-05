import yaml
import base64
import time
from datetime import datetime
from clients.ocp_routes import kubectl_apply
from templates import secrets


def prep_submitted_config(docs):
    content = []
    for gw_config in docs:
        content.append(yaml.dump(gw_config))
    file_content = "\n---\n".join(content)

    return file_content


def prep_and_apply_secret(ns: str, select_tag: str, content: str, root_path: str):
    out_filename = "%s/submitted_config_secret.yaml" % root_path

    ts = int(time.time())
    fmt_time = datetime.now().strftime("%Y.%m-%b.%d")

    config = base64.b64encode(content.encode('utf-8')).decode('utf-8')

    with open(out_filename, 'w') as out_file:
        out_file.write(secrets.SECRET.substitute(name="gwa-orig-%s" % (select_tag.replace('.', '-')),
                       ns=ns, select_tag=select_tag, config=config, timestamp=ts, fmt_time=fmt_time))
        out_file.write('\n---\n')

    kubectl_apply(out_filename)
