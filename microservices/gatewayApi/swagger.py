
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

from auth.token import OIDCDiscovery
from swagger_ui import api_doc
from jinja2 import Template


def setup_swagger_docs (app):
    conf = config.Config()
    log = logging.getLogger(__name__)

    try:
        ## Template the spec and write it to a temporary location
        discovery = OIDCDiscovery(conf.data['oidcBaseUrl'])
        tmpFile = "%s/v1.yaml" % conf.data['workingFolder']
        f = open("v1/spec/v1.yaml", "r")
        t = Template(f.read())
        f = open(tmpFile, "w")
        f.write(t.render(
            server_url = "/v1",
            tokeninfo_url = discovery["introspection_endpoint"],
            authorization_url = discovery["authorization_endpoint"],
            accesstoken_url = discovery["token_endpoint"]
        ))
        api_doc(app, config_path=tmpFile, url_prefix='/api/doc', title='API doc')
        log.info("Configured /api/doc")
    except:
        log.error("Failed to do OIDC Discovery, sleeping 5 seconds and trying again.")
        time.sleep(5)
        setup_swagger_docs(app)
