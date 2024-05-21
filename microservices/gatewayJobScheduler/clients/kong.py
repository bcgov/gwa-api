import os
import logging
from subprocess import Popen, PIPE
import shlex
import json

logger = logging.getLogger(__name__)

def get_routes():
    endpoint = "/routes"
    routes_list = []
    while True:
        p1 = Popen(shlex.split("curl %s%s" % (os.getenv('KONG_ADMIN_API_URL'), endpoint)), stdout=PIPE)
        run = Popen(shlex.split(
            "jq ."), stdin=p1.stdout, stdout=PIPE, stderr=PIPE)
        out, err = run.communicate()

        if run.returncode != 0:
            logger.error("Failed to get existing routes - %s - %s", out, err)
            raise OSError("Shell command returned error exit code")

        result = json.loads(out)
        routes_list = routes_list + result['data']

        if result['next'] == None:
            return routes_list
        endpoint = result['next']
