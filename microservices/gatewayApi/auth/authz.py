from flask import g, abort, make_response, jsonify

def enforce_authorization(namespace):

    if 'team' not in g.principal:
        abort(make_response(jsonify(error="Missing Claims."), 403))

    # Make sure namespace matches the 'team' claim
    team = g.principal['team']
    if team != namespace:
        abort(make_response(jsonify(error="Not authorized to use %s namespace." % namespace), 403))
