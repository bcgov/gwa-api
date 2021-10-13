from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import os
import requests
import logging
import time
from subprocess import Popen, PIPE
import json

logging.basicConfig(level=os.getenv('LOG_LEVEL', default=logging.DEBUG),
                    format='%(asctime)s-%(levelname)s-%(message)s', datefmt='%d-%b-%y %H:%M:%S')

load_dotenv()


def get_token():

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

    logging.debug("[get_token] %s" % r.status_code)
    json = r.json()
    return json['access_token']


def get_routes():
    args = [
        "kubectl", "get", "routes", "-l", "aps-generated-by=gwa-cli", "-o", "json"
    ]
    run = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = run.communicate()

    if run.returncode != 0:
        logging.error("Failed to get existing routes - %s - %s", out, err)
        raise Exception("Failed to get existing routes")

    return json.loads(out)['items']


def sync_routes():
    logging.info('This is token: ' + get_token())


scheduler = BackgroundScheduler()
scheduler.add_job(sync_routes, 'interval', seconds=os.getenv('SYNC_INTERVAL', default=900))
scheduler.start()

try:
    # This is here to simulate application activity (which keeps the main thread alive).
    while True:
        time.sleep(2)
except (KeyboardInterrupt, SystemExit):
    # Not strictly necessary if daemonic mode is enabled but should be done if possible
    scheduler.shutdown()
