import requests
from flask import current_app as app

def check_kong3_compatibility(namespace: str, config: dict) -> tuple[bool, str, list[str], dict | None]:
    """
    Check Kong 3.x compatibility of configuration using compatibility API
    Returns (is_compatible, message, failed_routes, kong2_config)
    """
    log = app.logger
    
    log.debug("[%s] - Initiating request to compatibility API" % namespace)
    rqst_url = app.config['compatibilityApiUrl'] + "/configs"
    
    try:
        res = requests.post(rqst_url, json=config)
        res.raise_for_status()
        
        data = res.json()
        log.debug("[%s] - Compatibility API result for Kong 3 compatibility check: %s" % (namespace, data["kong3_compatible"]))
        return (
            data["kong3_compatible"],
            data["message"],
            data["failed_routes"],
            data["kong2_output"]
        )
    except Exception as e:
        log.error("[%s] - Compatibility API error: %s" % (namespace, str(e)))
        return (True, "", [], {}) # Fail open - assume compatible if service unavailable 