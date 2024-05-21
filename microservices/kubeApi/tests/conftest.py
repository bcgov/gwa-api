import pytest
import os
import sys
from app import create_app
from fastapi.testclient import TestClient
from auth.basic_auth import verify_credentials
from clients.ocp_routes import get_gwa_ocp_routes, kubectl_delete, prepare_apply_routes, apply_routes, prepare_mismatched_routes, delete_routes
from clients.ocp_services import get_gwa_ocp_services, get_gwa_ocp_service_secrets, prepare_apply_services, apply_services, prepare_mismatched_services, delete_services
from unittest.mock import patch
from subprocess import Popen, PIPE, STDOUT
import logging
import logging.config

# @patch('clients.ocp_services.get_gwa_ocp_service_secrets')
# def mock_get_gwa_ocp_service_secrets():
#     return []

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""

    logging.config.dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] %(levelname)5s %(module)s.%(funcName)5s: %(message)s',
        }},
        'handlers': {'console': {
            'level': "DEBUG",
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
            'formatter': 'default'
        }},
        'loggers': {
            'uvicorn': {
                'propagate': True
            },
            'fastapi': {
                'propagate': True
            }
        },
        'root': {
            'level': "DEBUG",
            'handlers': ['console']
        }
    })

    app = create_app()

    def mock_verify_credentials():
        return True
    app.dependency_overrides[verify_credentials] = mock_verify_credentials

    yield app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return TestClient(app)


# @pytest.fixture
# def runner(app):
#     """A test runner for the app's Click commands."""
#     return app.test_cli_runner()