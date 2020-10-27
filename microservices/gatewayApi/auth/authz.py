from flask import g, abort, make_response, jsonify

def users_group_root():
    return 'ns'

def admins_group_root():
    return 'ns-admins'

def ns_claim():
    return 'namespace'

def enforce_authorization(namespace):
    the_ns_claim = ns_claim()

    if the_ns_claim not in g.principal:
        abort(make_response(jsonify(error="Missing Claims."), 403))

    # Make sure namespace matches the one in the claim
    # It can be in two formats: '/ns/<namespace>' or '<namespace>'
    ns = g.principal[the_ns_claim]
    if ns != namespace and ns != ('/%s/%s' % (users_group_root(), namespace)):
        abort(make_response(jsonify(error="Not authorized to use %s namespace." % namespace), 403))

def enforce_role_authorization(role):
    return
