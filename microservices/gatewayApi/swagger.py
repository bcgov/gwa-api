
try:  # Python 3.5+
    from http import HTTPStatus as HTTPStatus
except ImportError:
    from http import client as HTTPStatus
import logging
import os
import time
import config
from authlib.jose.errors import JoseError, ExpiredTokenError
from flask import Flask, g, jsonify, request, make_response, url_for, Response
from flask_compress import Compress
from flask_cors import CORS
import threading
import traceback, sys

from auth.token import OIDCDiscovery
from flask_swagger_ui import get_swaggerui_blueprint
from jinja2 import Template

def setup_swagger_docs (app, versions):
    conf = config.Config()
    log = logging.getLogger(__name__)

    try:
        swaggerui_blueprint = get_swaggerui_blueprint(
            '/docs',
            "/docs/%s/openapi.yaml" % versions[len(versions)-1],
            config={
            },
        )

        # blah = lambda: app.send_static_file(tmpFile)
        # app.view_functions['blah'] = blah
        @app.route("/docs/<ver>/openapi.yaml")
        def openapi_spec(ver:str):
            return Response(open("%s/%s.yaml" % (conf.data['workingFolder'], ver)).read(), mimetype='application/x-yaml')

        #app.add_url_rule("/%s/docs/openapi.yaml" % version, openapi_spec)
        app.register_blueprint(swaggerui_blueprint)

        for version in versions:
            ## Template the spec and write it to a temporary location
            discovery = OIDCDiscovery(conf.data['oidcBaseUrl'])
            tmpFile = "%s/%s.yaml" % (conf.data['workingFolder'], version)
            f = open("%s/spec/spec.yaml" % (version), "r")
            t = Template(f.read())
            f = open(tmpFile, "w")
            f.write(t.render(
                server_url = "/%s" % version,
                tokeninfo_url = discovery["introspection_endpoint"],
                authorization_url = discovery["authorization_endpoint"],
                accesstoken_url = discovery["token_endpoint"]
            ))

            
            log.info("Configured /%s/docs" % version)

    except:
        traceback.print_exc(file=sys.stdout)
        log.error("Failed to do OIDC Discovery for %s, sleeping 5 seconds and trying again." % version)
        time.sleep(5)
        setup_swagger_docs(app, version)

