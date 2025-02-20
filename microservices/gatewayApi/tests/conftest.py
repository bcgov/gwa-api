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
    mock_compatibility_api(mocker)

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
            if path == "/ns/mytest":
                return {"id": "g001"}
            elif path == "/ns/mytest2":
                return {"id": "g002"}
            elif path == "/ns/mytest3":
                return {"id": "g003"}
            elif path == "/ns/customcert":
                return {"id": "g004"}
            else:
                return {"id": "g001"}
        def get_group(id):
            if id == "g001":
                return {
                    "attributes": {
                        "perm-domains": [ ".api.gov.bc.ca", ".cluster.local" ]
                    }
                }
            elif id == "g002":
                return {
                    "attributes": {
                        "perm-data-plane": ["strict-dp"],
                        "perm-upstreams": [],
                        "perm-domains": [ ".api.gov.bc.ca", ".cluster.local" ]
                    }
                }
            elif id == "g003":
                return {
                    "attributes": {
                        "perm-data-plane": ["strict-dp"],
                        "perm-upstreams": ['ns1'],
                        "perm-domains": [ ".api.gov.bc.ca", ".cluster.local" ]
                    }
                }
            elif id == "g004":
                return {
                    "attributes": {
                        "perm-domains": [ ".api.gov.bc.ca", ".custom.gov.bc.ca" ]
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

def mock_compatibility_api(mocker):
    def mock_requests_post(url, json=None, **kwargs):
        if url == 'http://compatibility-api/configs':
            log.debug(f"Mocking compatibility API: {url}")
            class Response:
                def json(self):
                    # Check if any routes have regex without tilde
                    has_incompatible = False
                    failed_routes = []
                    
                    if json and "services" in json:
                        for service in json["services"]:
                            if "routes" in service:
                                for route in service["routes"]:
                                    if "paths" in route and "name" in route:
                                        for path in route["paths"]:
                                            if "*" in path and not path.startswith("~"):
                                                has_incompatible = True
                                                failed_routes.append(route["name"])
                    
                    message = (
                        "Gateway configuration is compatible with Kong 3." 
                        if not has_incompatible else
                        "WARNING: Kong 3 incompatible routes found.\n\n"
                        "APS will soon be updated to use Kong gateway version 3.\n"
                        "Kong 3 requires that regular expressions in route paths start with a '~' character.\n\n"
                        "For related information, please visit:\n"
                        "https://docs.konghq.com/deck/latest/3.0-upgrade\n\n"
                        "Please update the following routes:"
                    )
                    
                    return {
                        "kong3_compatible": not has_incompatible,
                        "message": message,
                        "failed_routes": failed_routes,
                        "kong2_output": json
                    }
                
                def raise_for_status(self):
                    if self.status_code != 200:
                        raise Exception(f"HTTP {self.status_code}")
                
                status_code = 200
                
            return Response()
        raise Exception(f"Unexpected URL: {url}")

    mocker.patch("clients.compatibility.requests.post", mock_requests_post)
