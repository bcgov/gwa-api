import json
from unittest import mock
from app import transform_data_by_ns

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
        snis = []
        assert json.dumps(transform_data_by_ns(routes, snis)) == '{"ns1": [{"name": "wild-ns-ns1-test.api.gov.bc.ca", "selectTag": "ns.ns1", "host": "test.api.gov.bc.ca", "sessionCookieEnabled": false, "dataClass": null, "dataPlane": "test-dp", "sslCertificateId": "default"}]}'

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
        snis = []
        assert json.dumps(transform_data_by_ns(routes, snis)) == '{"ns1": [{"name": "wild-ns-ns1-test.api.gov.bc.ca", "selectTag": "ns.ns1", "host": "test.api.gov.bc.ca", "sessionCookieEnabled": true, "dataClass": null, "dataPlane": "test-dp", "sslCertificateId": "default"}]}'

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
        snis = []
        assert json.dumps(transform_data_by_ns(routes, snis)) == '{"ns1": [{"name": "wild-ns-ns1-test.api.gov.bc.ca", "selectTag": "ns.ns1", "host": "test.api.gov.bc.ca", "sessionCookieEnabled": false, "dataClass": "high", "dataPlane": "test-dp", "sslCertificateId": "default"}]}'

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
        snis = [
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
        assert json.dumps(transform_data_by_ns(routes, snis)) == '{"ns1": [{"name": "wild-ns-ns1-test.custom.gov.bc.ca", "selectTag": "ns.ns1", "host": "test.custom.gov.bc.ca", "sessionCookieEnabled": false, "dataClass": null, "dataPlane": "test-dp", "sslCertificateId": "41d14845-669f-4dcd-aff2-926fb32a4b25"}]}'


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
