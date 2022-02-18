from sys import exc_info
import os
import requests
import logging
from subprocess import Popen, PIPE
import shlex
import traceback
import schedule
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
        if ns_group_summary is not None:
            ns_group = self.keycloak_admin.get_group(ns_group_summary['id'])
            attrs = ns_group['attributes']
            return attrs
        # returning empty dict when namespace or group not found in keycloak
        return {}


def get_routes():
    try:
        endpoint = "/routes"
        routes_list = []
        while True:
            p1 = Popen(shlex.split("curl %s%s" % (os.getenv('KONG_ADMIN_API_URL'), endpoint)), stdout=PIPE)
            run = Popen(shlex.split(
                "jq ."), stdin=p1.stdout, stdout=PIPE, stderr=PIPE)
            out, err = run.communicate()

            if run.returncode != 0:
                logger.error("Failed to get existing routes - %s - %s", out, err)
                clear('sync-routes')
                exit(1)

            result = json.loads(out)
            routes_list = routes_list + result['data']

            if result['next'] == None:
                return routes_list
            endpoint = result['next']

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
    for ns in data:
        url = os.getenv('KUBE_API_URL') + '/namespaces/%s/routes/sync' % ns
        response = requests.post(url, headers=headers, json=data[ns], auth=(
            os.getenv('KUBE_API_USER'), os.getenv('KUBE_API_PASS')))

        if response.status_code not in [200, 201]:
            logging.error('Failed to sync routes - %s' % response.text)
            clear('sync-routes')
            exit(1)


def transform_data_by_ns(data):
    ns_svc = NamespaceService()
    try:
        ns_dict = {}
        ns_attr_dict = {}
        for route_obj in data:
            select_tag = get_select_tag(route_obj['tags'])
            namespace = select_tag.split(".")[1]

            if namespace not in ns_dict:
                ns_dict[namespace] = []
                ns_attr_dict[namespace] = ns_svc.get_namespace_attributes(namespace)

            # check if namespace has data plane attribute
            if ns_attr_dict[namespace].get('perm-data-plane', [''])[0] == os.getenv('DATA_PLANE'):
                for host in route_obj['hosts']:
                    name = 'wild-%s-%s' % (select_tag.replace(".", "-"), host)
                    ns_dict[namespace].append({"name": name, "selectTag": select_tag, "host": host,
                                               "dataPlane": os.getenv('DATA_PLANE')})
        return ns_dict
    except Exception as err:
        traceback.print_exc()
        logger.error("Error transforming data. %s" % str(err))


def get_select_tag(tags):
    qualifiers = ['dev', 'test', 'prod']
    valid_select_tags = []
    required_tag = None
    for tag in tags:
        if tag.startswith("ns."):
            required_tag = tag
            if len(tag.split(".")) > 2:
                required_tag = tag
                break
    return required_tag


# Run all the jobs for once irrespective of the interval
schedule.run_all()

# Run all the jobs with specified interval
while True:
    run_pending()
    time.sleep(1)
