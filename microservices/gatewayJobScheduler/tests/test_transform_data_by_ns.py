import json
import pytest
from unittest import mock
from app import transform_data_by_ns
from conftest import SAMPLE_CERT, SAMPLE_KEY

def test_happy_transform_data_by_ns():
    with mock.patch('clients.namespace.admin_api') as mock_admin_api:
        set_mock_admin_api_response(mock_admin_api)

        routes = [
            {
                "name": "route-1",
                "tags": [ "ns.ns1"],
                "hosts": [
                    "test.api.gov.bc.ca"
                ]
            }
        ]
        certs = []
        cert_snis = []
        expected_value = {
            "ns1": [
                {
                    "name": "wild-ns-ns1-test.api.gov.bc.ca",
                    "selectTag": "ns.ns1",
                    "host": "test.api.gov.bc.ca",
                    "sessionCookieEnabled": False,
                    "dataClass": None,
                    "dataPlane": "test-dp",
                    "sslCertificateSerialNumber": None,
                    "certificates": None
                }
            ]
        }
        assert json.dumps(transform_data_by_ns(routes, certs, cert_snis)) == json.dumps(expected_value)

def test_happy_transform_data_by_ns_with_override_session_cookie():
    with mock.patch('clients.namespace.admin_api') as mock_admin_api:
        set_mock_admin_api_response(mock_admin_api)

        routes = [
            {
                "name": "route-1",
                "tags": [ "ns.ns1", "aps.route.session.cookie.enabled"],
                "hosts": [
                    "test.api.gov.bc.ca"
                ]
            }
        ]
        certs = []
        cert_snis = []
        expected_value = {
            "ns1": [{
                "name": "wild-ns-ns1-test.api.gov.bc.ca",
                "selectTag": "ns.ns1",
                "host": "test.api.gov.bc.ca",
                "sessionCookieEnabled": True,
                "dataClass": None,
                "dataPlane": "test-dp",
                "sslCertificateSerialNumber": None,
                "certificates": None
            }]
        }
        assert json.dumps(transform_data_by_ns(routes, certs, cert_snis)) == json.dumps(expected_value)

def test_happy_transform_data_by_ns_with_override_data_plane():
    with mock.patch('clients.namespace.admin_api') as mock_admin_api:
        set_mock_admin_api_response(mock_admin_api)

        routes = [
            {
                "name": "route-1",
                "tags": [ "ns.ns1", "aps.route.dataclass.high"],
                "hosts": [
                    "test.api.gov.bc.ca"
                ]
            }
        ]
        certs = []
        cert_snis = []
        expected_value = {
            "ns1": [{
                "name": "wild-ns-ns1-test.api.gov.bc.ca",
                "selectTag": "ns.ns1",
                "host": "test.api.gov.bc.ca",
                "sessionCookieEnabled": False,
                "dataClass": "high",
                "dataPlane": "test-dp",
                "sslCertificateSerialNumber": None,
                "certificates": None
            }]
        }
        assert json.dumps(transform_data_by_ns(routes, certs, cert_snis)) == json.dumps(expected_value)

def test_happy_transform_data_by_ns_with_custom_domain():
    with mock.patch('clients.namespace.admin_api') as mock_admin_api:
        set_mock_admin_api_response(mock_admin_api)

        routes = [
            {
                "name": "route-1",
                "tags": [ "ns.ns1"],
                "hosts": [
                    "test.custom.gov.bc.ca"
                ]
            }
        ]
        certs = [
                {
                    "id": "41d14845-669f-4dcd-aff2-926fb32a4b25",
                    "cert": SAMPLE_CERT,
                    "created_at": 1731713874,
                    "tags": [
                        "ns.ns1"
                    ],
                    "key": SAMPLE_KEY,
                }
        ]
        cert_snis = [
            {
                "name": "test.custom.gov.bc.ca",
                "id": "79009c9e-0f4d-40b5-9707-bf2fe9f50502",
                "created_at": 1731713874,
                "certificate": "41d14845-669f-4dcd-aff2-926fb32a4b25",
                "tags": [
                    "ns.ns1"
                ]
            }
        ]
        expected_value = {
            "ns1": [{
                "name": "wild-ns-ns1-test.custom.gov.bc.ca",
                "selectTag": "ns.ns1",
                "host": "test.custom.gov.bc.ca",
                "sessionCookieEnabled": False,
                "dataClass": None,
                "dataPlane": "test-dp",
                "sslCertificateSerialNumber": "1",
                "certificates": [
                    {
                        "id": "41d14845-669f-4dcd-aff2-926fb32a4b25",
                        "cert": SAMPLE_CERT,
                        "created_at": 1731713874,
                        "tags": [
                            "ns.ns1"
                        ],
                        "key": SAMPLE_KEY,
                        "snis": [
                            "test.custom.gov.bc.ca"
                        ]
                    }
                ]
            }]
        }
        assert json.dumps(transform_data_by_ns(routes, certs, cert_snis)) == json.dumps(expected_value)

def test_missing_cert_transform_data_by_ns_with_custom_domain(caplog):
    with mock.patch('clients.namespace.admin_api') as mock_admin_api:
        set_mock_admin_api_response(mock_admin_api)

        routes = [
            {
                "name": "route-1",
                "tags": [ "ns.ns1"],
                "hosts": [
                    "test.custom.gov.bc.ca"
                ]
            }
        ]
        certs = [
                {
                    "id": "41d14845-669f-4dcd-aff2-926fb32a4b25",
                    "cert": "CERT",
                    "created_at": 1731713874,
                    "tags": [
                        "ns.ns1"
                    ],
                    "key": "KEY",
                }
        ]
        cert_snis = [
            {
                "name": "other.custom.gov.bc.ca",
                "id": "79009c9e-0f4d-40b5-9707-bf2fe9f50502",
                "created_at": 1731713874,
                "certificate": "41d14845-669f-4dcd-aff2-926fb32a4b25",
                "tags": [
                    "ns.ns1"
                ]
            }
        ]
        
        expected_error = "Error transforming data. Certificate not found for host test.custom.gov.bc.ca"
        transform_data_by_ns(routes, certs, cert_snis)
        assert expected_error in caplog.text


def set_mock_admin_api_response(dt):
    class mock_admin_api:
        def get_group_by_path(path, **kwargs):
            return {
                "id": "group-1"
            }
        def get_group(id):
            return {
                "attributes": {
                    "perm-data-plane": ["test-dp"]
                }
            }
    dt.return_value = mock_admin_api
