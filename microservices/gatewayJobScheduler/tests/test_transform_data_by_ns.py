import json
import pytest
from unittest import mock
from app import transform_data_by_ns
from conftest import SAMPLE_CERT, SAMPLE_KEY


def _create_mock_kc():
    mock_kc = mock.Mock()
    mock_kc.get_group_by_path.return_value = {"id": "group-1"}
    mock_kc.get_group.return_value = {
        "attributes": {
            "perm-data-plane": ["test-dp"]
        }
    }
    return mock_kc


def test_happy_transform_data_by_ns():
    mock_kc = _create_mock_kc()
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
    assert json.dumps(transform_data_by_ns(mock_kc, routes, certs, cert_snis)) == json.dumps(expected_value)


def test_happy_transform_data_by_ns_with_override_session_cookie():
    mock_kc = _create_mock_kc()
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
    assert json.dumps(transform_data_by_ns(mock_kc, routes, certs, cert_snis)) == json.dumps(expected_value)


def test_happy_transform_data_by_ns_with_override_data_plane():
    mock_kc = _create_mock_kc()
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
    assert json.dumps(transform_data_by_ns(mock_kc, routes, certs, cert_snis)) == json.dumps(expected_value)


def test_happy_transform_data_by_ns_with_custom_domain():
    mock_kc = _create_mock_kc()
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
            "certificate": {
                "id": "41d14845-669f-4dcd-aff2-926fb32a4b25"
            },
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
    assert json.dumps(transform_data_by_ns(mock_kc, routes, certs, cert_snis)) == json.dumps(expected_value)


def test_missing_cert_transform_data_by_ns_with_custom_domain():
    mock_kc = _create_mock_kc()
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
            "certificate": {
                "id": "41d14845-669f-4dcd-aff2-926fb32a4b25"
            },
            "tags": [
                "ns.ns1"
            ]
        }
    ]

    with pytest.raises(Exception, match="Certificate not found for host test.custom.gov.bc.ca"):
        transform_data_by_ns(mock_kc, routes, certs, cert_snis)
