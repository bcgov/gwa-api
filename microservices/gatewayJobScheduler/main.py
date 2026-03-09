import os
import requests
from sys import exc_info
import logging
import traceback
from app import transform_data_by_ns, get_namespaces_with_perm_data_plane
from clients.keycloak import admin_api
from clients.kong import get_records
import schedule
from schedule import every, repeat, run_pending, clear
import time

# using root logger
logging.basicConfig(level=os.getenv('LOG_LEVEL', default=logging.DEBUG),
                    format='%(asctime)s-%(levelname)s-%(message)s', datefmt='%d-%b-%y %H:%M:%S')

logger = logging.getLogger(__name__)

def validate_keycloak_connection(kc):
    """Verify Keycloak connectivity before performing any sync operations"""
    kc.get_groups(query={"max": 1})
    logger.info("Keycloak connection validated")

@repeat(every(int(os.getenv('SYNC_INTERVAL'))).seconds.tag('sync-routes'))
def sync_routes():
    headers = {
        'accept': 'application/json',
        'cache-control': 'no-cache',
        'content-type': 'application/json'
    }
    try:
        routes = get_records('routes')
        certs = get_records('certificates')
        cert_snis = get_records('snis')
    except:
        traceback.print_exc()
        logger.error('Failed to get existing routes - %s' % (exc_info()[0]))
        clear('sync-routes')
        exit(1)

    try:
        kc = admin_api()
        validate_keycloak_connection(kc)
    except Exception:
        traceback.print_exc()
        logger.error('Failed to connect to Keycloak')
        clear('sync-routes')
        exit(1)

    try:
        # Get Gold namespaces from Keycloak
        perm_data_plane_value = os.getenv('DATA_PLANE')
        namespaces = get_namespaces_with_perm_data_plane(kc, perm_data_plane_value)
        # Transform route data from Kong
        data = transform_data_by_ns(kc, routes, certs, cert_snis)
    except Exception as err:
        traceback.print_exc()
        logger.error('Failed to process namespace/route data - %s' % str(err))
        clear('sync-routes')
        exit(1)

    # Add missing namespaces with no routes
    for ns in namespaces:
        if ns not in data:
            data[ns] = []

    if len(routes) > 0 and all(len(v) == 0 for v in data.values()):
        logger.error(
            "Kong has %d routes but transformation produced zero route entries — aborting sync" % len(routes))
        clear('sync-routes')
        exit(1)

    for ns in data:
        url = os.getenv('KUBE_API_URL') + '/namespaces/%s/routes/sync' % ns
        response = requests.post(url, headers=headers, json=data[ns], auth=(
            os.getenv('KUBE_API_USER'), os.getenv('KUBE_API_PASS')))

        if response.status_code not in [200, 201]:
            logging.error('Failed to sync routes - %s' % response.text)
            clear('sync-routes')
            exit(1)

# Run all the jobs for once irrespective of the interval
schedule.run_all()

# Run all the jobs with specified interval
while True:
    run_pending()
    time.sleep(1)
