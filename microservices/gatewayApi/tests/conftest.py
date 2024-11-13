import pytest
import os
import sys
import json
from functools import wraps
import logging
log = logging.getLogger(__name__)
from logging.config import dictConfig

# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '%(asctime)s [%(process)3d] %(levelname)5s %(module)-15s: %(message)s',
    }},
    'handlers': {'app': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'DEBUG',
        'handlers': ['app']
    }
})


@pytest.fixture
def app(mocker):
    """Create and configure a new app instance for each test."""

    mock_auth(mocker)
    mock_keycloak(mocker)
    mock_kong(mocker)
    mock_portal_feeder(mocker)
    mock_deck(mocker)
    mock_kubeapi(mocker)

    from app import create_app
    app = create_app()
    yield app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

def mock_auth(mocker):
    def mock_decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function

    mocker.patch('auth.auth.admin_jwt', return_value=mock_decorator)

    mocker.patch("auth.uma.enforce", return_value=True)

def mock_keycloak(mocker):
    class mock_kc_admin:
        def get_group_by_path(path, search_in_subgroups):
            if path.endswith("customcert"):
                return {
                    "id": "g002"
                }
            return {
                "id": "g001"
            }
        def get_group(id):
            if id == "g002":
                return {
                    "attributes": {
                        "perm-domains": [ ".api.gov.bc.ca", ".custom.gov.bc.ca" ]
                    }
                }
            return {
                "attributes": {
                    "perm-domains": [ ".api.gov.bc.ca", ".cluster.local" ]
                }
            }
    mocker.patch("v2.services.namespaces.admin_api", return_value=mock_kc_admin)

def mock_kong(mocker):

    def mock_requests_get(path):
        if (path == 'http://kong/routes'):
            class Response:
                def json():
                    return {
                        "data": [
                            {
                                "name": "ns1-route",
                                "tags": [ "ns.ns1" ],
                                "hosts": [
                                    "ns1-service.api.gov.bc.ca"
                                ]
                            }
                        ],
                        "next": None
                    }
            return Response
        elif (path == 'http://kong/certificates?tags=gwa.ns.mytest' or
              path == 'http://kong/certificates?tags=gwa.ns.sescookie' or
              path == 'http://kong/certificates?tags=gwa.ns.dclass' or
              path == 'http://kong/certificates?tags=gwa.ns.customcert'):
            class Response:
                def json():
                    return {
                        "data": [],
                        "next": None
                    }
            return Response
        elif (path == 'http://kong/certificates?tags=ns.customcert'):
            class Response:
                def json():
                    return {
                        "next": None,
                        "data": [
                            {
                                "id": "41d14845-669f-4dcd-aff2-926fb32a4b25",
                                "snis": [
                                    "test.custom.gov.bc.ca"
                                ],
                                "tags": [
                                    "ns.customcert",
                                ],
                                "cert": "CERT",
                                "key": "KEY"
                            }
                        ]
                    }
            return Response

        else:
            raise Exception(path)
    mocker.patch("clients.kong.requests.get", mock_requests_get)

def mock_portal_feeder(mocker):

    def mock_requests_put(path, headers, json, timeout):
        if (path == 'http://portal/feed/Activity'):
            class Response:
                status_code = 200
                # def json():
                #     return {}
            return Response
        else:
            raise Exception(path)
    mocker.patch("clients.portal.requests.put", mock_requests_put)

def mock_deck(mocker):
    class decoded_response:
        def __init__ (self, output):
            self.output = output
        def decode(self, utf):
            return self.output

    class mock_popen_instance:
        def __init__ (self, output):
            self.output = output
        def communicate(self):
            return decoded_response(self.output), None
        returncode = 0

    mock_output = "Deck reported no changes"
    mocker.patch("v2.routes.gateway.Popen", return_value=mock_popen_instance(mock_output))

def mock_kubeapi(mocker):

    def mock_requests_put(self, url, data=None, **kwargs):
        if (url == 'http://kube-api/namespaces/mytest/routes'):
            class Response:
                status_code = 201
                # def json():
                #     return {}
            return Response
        elif (url == 'http://kube-api/namespaces/sescookie/routes'):
            class Response:
                status_code = 201
            matched = {
                'hosts': ['myapi.api.gov.bc.ca'], 
                'ns_attributes': {'perm-domains': ['.api.gov.bc.ca', '.cluster.local']}, 
                'overrides': {
                    'aps.route.session.cookie.enabled': ['myapi.api.gov.bc.ca'],
                    "aps.route.dataclass.low": [],
                    "aps.route.dataclass.medium": [],
                    "aps.route.dataclass.high": [],
                    "aps.route.dataclass.public": []
                }, 
                'select_tag': 'ns.sescookie.dev',
                'certificates': []
            }

            assert json.dumps(kwargs['json'], sort_keys=True) == json.dumps(matched, sort_keys=True)
            return Response
        elif (url == 'http://kube-api/namespaces/dclass/routes'):
            class Response:
                status_code = 201
            matched = {
                'hosts': ['myapi.api.gov.bc.ca'], 
                'ns_attributes': {'perm-domains': ['.api.gov.bc.ca', '.cluster.local']}, 
                'overrides': {
                    'aps.route.session.cookie.enabled': [],
                    "aps.route.dataclass.low": [],
                    "aps.route.dataclass.medium": [],
                    "aps.route.dataclass.high": ['myapi.api.gov.bc.ca'],
                    "aps.route.dataclass.public": []
                }, 
                'select_tag': 'ns.dclass.dev',
                'certificates': []
            }

            assert json.dumps(kwargs['json'], sort_keys=True) == json.dumps(matched, sort_keys=True)
            return Response
        elif (url == 'http://kube-api/namespaces/customcert/routes'):
            class Response:
                status_code = 201
            matched = {
                'hosts': ['test.custom.gov.bc.ca'], 
                'ns_attributes': {'perm-domains': ['.api.gov.bc.ca', '.custom.gov.bc.ca']}, 
                'overrides': {
                    'aps.route.session.cookie.enabled': [],
                    "aps.route.dataclass.low": [],
                    "aps.route.dataclass.medium": [],
                    "aps.route.dataclass.high": [],
                    "aps.route.dataclass.public": []
                }, 
                'select_tag': 'ns.customcert',
                'certificates': [
                    {
                        "id": "41d14845-669f-4dcd-aff2-926fb32a4b25",
                        "snis": [
                            "test.custom.gov.bc.ca"
                        ],
                        "tags": [
                            "ns.customcert",
                        ],
                        "cert": "CERT",
                        "key": "KEY"
                    }
                ]
            }

            assert json.dumps(kwargs['json'], sort_keys=True) == json.dumps(matched, sort_keys=True)
            return Response
        elif (url == 'http://kube-api/namespaces/ns1/routes'):
            class Response:
                status_code = 201
                # def json():
                #     return {}
            return Response
        else:
            raise Exception(url)
    
    def mock_requests_get(self, url, **kwards):
        if (url == 'http://kube-api/namespaces/mytest/local_tls' or
            url == 'http://kube-api/namespaces/sescookie/local_tls' or
            url == 'http://kube-api/namespaces/dclass/local_tls' or
            url == 'http://kube-api/namespaces/customcert/local_tls'):
            class Response:
                status_code = 200
                def json():
                    return {}
            return Response

        else:
            raise Exception(url)

    mocker.patch("clients.portal.requests.Session.put", mock_requests_put)
    mocker.patch("clients.portal.requests.Session.get", mock_requests_get)
