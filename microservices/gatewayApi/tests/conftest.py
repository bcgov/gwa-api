import pytest
import os
import sys
from functools import wraps

# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



@pytest.fixture
def app(mocker):
    """Create and configure a new app instance for each test."""

    mock_auth(mocker)
    mock_keycloak(mocker)
    mock_kong(mocker)
    mock_portal_feeder(mocker)
    mock_deck(mocker)

    #mocker.patch("auth.authz.enforce_authorization", return_value=True)

    # def mock_resource_protector():
    #     raise Exception ("Hhu")

    #     return True
    # mocker.patch("authlib.integrations.flask_oauth2.ResourceProtector", return_value=mock_resource_protector)
    # mocker.patch("auth.auth.do_validate", return_value=mock_resource_protector)
    #mocker.patch("v2.routes.gateway.uma_enforce", mock_resource_protector)
    #mocker.patch("clients.keycloak.admin_api", return_value=mock_kc_admin)


    from app import create_app

    app = create_app()

    yield app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


# @pytest.fixture
# def runner(app):
#     """A test runner for the app's Click commands."""
#     return app.test_cli_runner()

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
            return {
                "id": "g001"
            }
        def get_group(id):
            return {
                "attributes": {

                }
            }
    mocker.patch("v2.services.namespaces.admin_api", return_value=mock_kc_admin)

def mock_kong(mocker):

    def mock_requests_get(path):
        if (path == 'http://kong/routes'):
            class Response:
                def json():
                    return {
                        "data": [],
                        "next": None
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