from functools import wraps
from flask import request, abort, make_response, Response, jsonify, g
from clients.uma.kcprotect import check_permissions, get_token
from clients.uma.resourceset import map_res_name_to_id

def enforce (resource, scope):
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
