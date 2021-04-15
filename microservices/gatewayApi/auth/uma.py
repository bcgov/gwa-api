from functools import wraps
from flask import request, abort, make_response, Response, jsonify, g
from config import Config

from authlib.integrations.flask_oauth2 import ResourceProtector
from auth.token import RemoteToken, OIDCTokenValidator

from clients.kcprotect import check_permissions, map_res_name_to_id, get_token

def enforce (resource, scope):
    print("[enforce] %s %s" % (resource, scope))
    pat = get_token()
    rsid = map_res_name_to_id (pat['access_token'], resource)
    return check_permissions (g.token_string, [("permission", "%s#%s" % ( rsid, scope ))])

def uma_enforce(resource_arg_name, opt_scope):
    def decorator (f):
        @wraps(f)
        def decorated(*args, **kwargs):
            resource = kwargs[resource_arg_name]
            scope = opt_scope
            if scope is None and 'scope' in kwargs:
                scope = kwargs['scope']
            if enforce(resource, scope) == False:
                abort(make_response(jsonify(error="Not authorized to access %s %s with %s" % (resource_arg_name, resource, scope)), 403))
            return f(*args, **kwargs)
        return decorated
    return decorator
