from sys import exc_info
from dotenv import load_dotenv
import os
import requests
import logging
from subprocess import Popen, PIPE
import shlex
import traceback
from schedule import every, repeat, run_pending, clear
import time
import json

# using root logger
logging.basicConfig(level=os.getenv('LOG_LEVEL', default=logging.DEBUG),
                    format='%(asctime)s-%(levelname)s-%(message)s', datefmt='%d-%b-%y %H:%M:%S')

load_dotenv()


def get_token():
    try:
        tokenUrl = "%s/realms/%s/protocol/openid-connect/token" % (os.getenv('KC_SERVER_URL'), os.getenv('KC_REALM'))

        data = {
            "grant_type": "client_credentials",
            "client_id": os.getenv('KC_RES_SVR_CLIENT_ID'),
            "client_secret": os.getenv('KC_RES_SVR_CLIENT_SECRET'),
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        print(tokenUrl)
        r = requests.post(tokenUrl, headers=headers, data=data)
        if r.status_code not in [200, 201]:
            logging.error('Failed to get token')
        logging.debug("[get_token] %s" % r.status_code)
        json = r.json()
        return json['access_token']
    except:
        traceback.print_exc()
        logging.error("Failed to get token. %s" % (exc_info()[0]))
        clear('sync-routes')
        exit(1)


def get_routes():
    try:
        p1 = Popen(shlex.split("curl %s/routes" % os.getenv('KONG_ADMIN_API_URL')), stdout=PIPE)
        run = Popen(shlex.split(
            "jq '.data'"), stdin=p1.stdout, stdout=PIPE, stderr=PIPE)
        out, err = run.communicate()

        if run.returncode != 0:
            logging.error("Failed to get existing routes - %s - %s", out, err)
            clear('sync-routes')
            exit(1)

        return json.loads(out)
    except:
        traceback.print_exc()
        logging.error('Failed to get existing routes - %s' % (exc_info()[0]))
        clear('sync-routes')
        exit(1)


@repeat(every(int(os.getenv('SYNC_INTERVAL'))).seconds.tag('sync-routes'))
def sync_routes():
    headers = {
        'accept': 'application/json',
        'authorization': 'bearer %s' % get_token(),
        'cache-control': 'no-cache',
        'content-type': 'application/json'
    }
    data = transform_data(get_routes())  # update kdc to cdc
    # url = os.getenv('GWA_KUBE_API_DR_URL') + '/sync/routes'
    # response = requests.post(url, headers=headers, json=data)

    # if response.status_code not in [200, 201]:
    #     logging.error('Failed to sync routes - %s' % response.text)
    #     clear('sync-routes')
    #     exit(1)


def transform_data(data):
    new_data = []
    for route_obj in data:
        new_route_obj = {}
        new_route_obj['selectTag'] = route_obj['tags'][0]
        new_route_obj['host'] = route_obj['hosts'][0]
        new_route_obj['namespace'] = route_obj['tags'][0].split(".")[1]
        new_route_obj['name'] = 'wild-%s-%s' % (route_obj['tags'][0].replace(".", "-"), route_obj['hosts'][0])
        new_data.append(new_route_obj)
    print(new_data)


while True:
    run_pending()
    time.sleep(1)
