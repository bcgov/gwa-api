import os
import logging
import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30  # seconds

def get_records(record_type):
    """
    Get all records of a specified type from Kong Admin API.

    Args:
        record_type (str): Type of records to fetch ('routes', 'certificates' or 'snis')

    Returns:
        list: List of records

    Raises:
        ValueError: If invalid record_type is provided
        RuntimeError: If the Admin API returns a non-2xx status or a body without a
            "data" list (e.g. the DP admin cache returns 503 when no config is loaded)
        requests.RequestException: If the request itself fails
    """
    if record_type not in ['routes', 'certificates', 'snis']:
        raise ValueError("record_type must be either 'routes', 'certificates' or 'snis'")

    base_url = os.getenv('KONG_ADMIN_API_URL')
    endpoint = "/%s" % record_type
    records_list = []

    while True:
        response = requests.get(base_url + endpoint, timeout=REQUEST_TIMEOUT)

        if not 200 <= response.status_code < 300:
            logger.error("Failed to get existing %s - GET %s returned HTTP %s: %s" % (
                record_type, endpoint, response.status_code, response.text[:200]))
            raise RuntimeError("Kong Admin API returned HTTP %s for %s" % (response.status_code, endpoint))

        result = response.json()
        if not isinstance(result, dict) or not isinstance(result.get('data'), list):
            logger.error("Failed to get existing %s - GET %s returned no data list: %s" % (
                record_type, endpoint, response.text[:200]))
            raise RuntimeError("Kong Admin API returned no data list for %s" % endpoint)

        records_list = records_list + result['data']

        if result.get('next') is None:
            return records_list
        endpoint = result['next']
