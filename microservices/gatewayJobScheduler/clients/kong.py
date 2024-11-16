import os
import logging
from subprocess import Popen, PIPE
import shlex
import json

logger = logging.getLogger(__name__)

def get_records(record_type):
    """
    Get all records of a specified type from Kong Admin API.
    
    Args:
        record_type (str): Type of records to fetch ('routes' or 'snis')
    
    Returns:
        list: List of records
    
    Raises:
        OSError: If the shell command fails
        ValueError: If invalid record_type is provided
    """
    if record_type not in ['routes', 'snis']:
        raise ValueError("record_type must be either 'routes' or 'snis'")

    endpoint = "/%s" % record_type
    records_list = []
    
    while True:
        p1 = Popen(shlex.split("curl %s%s" % (os.getenv('KONG_ADMIN_API_URL'), endpoint)), stdout=PIPE)
        run = Popen(shlex.split(
            "jq ."), stdin=p1.stdout, stdout=PIPE, stderr=PIPE)
        out, err = run.communicate()

        if run.returncode != 0:
            logger.error("Failed to get existing %s - %s - %s" % (record_type, out, err))
            raise OSError("Shell command returned error exit code")

        result = json.loads(out)
        records_list = records_list + result['data']

        if result['next'] == None:
            return records_list
        endpoint = result['next']
