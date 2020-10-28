import config

conf = config.Config().data

def mask (payload):
    # Need to mask the redis details
    redis_pswd = conf['plugins']['rate_limiting']['redis_password']
    redis_host = conf['plugins']['rate_limiting']['redis_host']
    returned = payload
    for val in [redis_pswd, redis_host]:
        returned = returned.replace(val, '****')
    return returned
