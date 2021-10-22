from sys import exc_info
import os
import requests
import logging
from subprocess import Popen, PIPE
import shlex
import traceback
from clients.keycloak import admin_api
from schedule import every, repeat, run_pending, clear
import time
import json
# from dotenv import load_dotenv
import traceback

# using root logger
logging.basicConfig(level=os.getenv('LOG_LEVEL', default=logging.DEBUG),
                    format='%(asctime)s-%(levelname)s-%(message)s', datefmt='%d-%b-%y %H:%M:%S')

logger = logging.getLogger(__name__)

# load_dotenv()


class NamespaceService:

    def __init__(self):
        self.keycloak_admin = admin_api()

    def get_namespace_attributes(self, namespace):
        ns_group_summary = self.keycloak_admin.get_group_by_path(
            path="/%s/%s" % ('ns', namespace), search_in_subgroups=True)
        ns_group = self.keycloak_admin.get_group(ns_group_summary['id'])
        attrs = ns_group['attributes']
        return attrs


def get_routes():
    try:
        p1 = Popen(shlex.split("curl %s/routes" % os.getenv('KONG_ADMIN_API_URL')), stdout=PIPE)
        run = Popen(shlex.split(
            "jq '.data'"), stdin=p1.stdout, stdout=PIPE, stderr=PIPE)
        out, err = run.communicate()

        if run.returncode != 0:
            logger.error("Failed to get existing routes - %s - %s", out, err)
            clear('sync-routes')
            exit(1)

        return json.loads(out)
    except:
        traceback.print_exc()
        logger.error('Failed to get existing routes - %s' % (exc_info()[0]))
        clear('sync-routes')
        exit(1)


@repeat(every(int(os.getenv('SYNC_INTERVAL'))).seconds.tag('sync-routes'))
def sync_routes():
    headers = {
        'accept': 'application/json',
        'cache-control': 'no-cache',
        'content-type': 'application/json'
    }

    data = transform_data_by_ns(get_routes())
    logger.debug(data)
    for ns in data:
        url = os.getenv('KUBE_API_URL') + '/namespaces/%s/routes/sync' % ns
        response = requests.post(url, headers=headers, json=data[ns], auth=(
            os.getenv('KUBE_API_USER'), os.getenv('KUBE_API_PASS')))

        if response.status_code not in [200, 201]:
            logging.error('Failed to sync routes - %s' % response.text)
            clear('sync-routes')
            exit(0)


def transform_data_by_ns(data):
    ns_svc = NamespaceService()
    try:
        ns_dict = {}
        ns_attr_dict = {}
        for route_obj in data:
            select_tag = route_obj['tags'][0]
            host = route_obj['hosts'][0]
            namespace = route_obj['tags'][0].split(".")[1]
            name = 'wild-%s-%s' % (route_obj['tags'][0].replace(".", "-"), route_obj['hosts'][0])

            if namespace not in ns_dict:
                ns_dict[namespace] = []
                ns_attr_dict[namespace] = ns_svc.get_namespace_attributes(namespace)

            # check if namespace has data plane attribute
            if ns_attr_dict[namespace].get('perm-data-plane', [''])[0] == os.getenv('DATA_PLANE'):
                ns_dict[namespace].append({"name": name, "selectTag": select_tag, "host": host})

        return ns_dict
    except:
        traceback.print_exc()
        logger.error("Error transforming data. %s" % str(data))


while True:
    run_pending()
    time.sleep(1)
