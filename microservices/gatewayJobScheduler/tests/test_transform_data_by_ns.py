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
        certs = []
        assert json.dumps(transform_data_by_ns(routes, certs)) == '{"ns1": [{"name": "wild-ns-ns1-test.api.gov.bc.ca", "selectTag": "ns.ns1", "host": "test.api.gov.bc.ca", "sessionCookieEnabled": false, "dataClass": null, "dataPlane": "test-dp", "customCertificateId": null}]}'

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
        assert json.dumps(transform_data_by_ns(routes, certs)) == '{"ns1": [{"name": "wild-ns-ns1-test.api.gov.bc.ca", "selectTag": "ns.ns1", "host": "test.api.gov.bc.ca", "sessionCookieEnabled": true, "dataClass": null, "dataPlane": "test-dp", "customCertificateId": null}]}'

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
        assert json.dumps(transform_data_by_ns(routes, certs)) == '{"ns1": [{"name": "wild-ns-ns1-test.api.gov.bc.ca", "selectTag": "ns.ns1", "host": "test.api.gov.bc.ca", "sessionCookieEnabled": false, "dataClass": "high", "dataPlane": "test-dp", "customCertificateId": null}]}'

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
                "snis": [
                    "test.custom.gov.bc.ca"
                ],
                "tags": [
                    "ns.ns1",
                ],
                "cert": "CERT",
                "key": "KEY"
            }
        ]
        assert json.dumps(transform_data_by_ns(routes, certs)) == '{"ns1": [{"name": "wild-ns-ns1-test.custom.gov.bc.ca", "selectTag": "ns.ns1", "host": "test.custom.gov.bc.ca", "sessionCookieEnabled": false, "dataClass": null, "dataPlane": "test-dp", "customCertificateId": "41d14845-669f-4dcd-aff2-926fb32a4b25"}]}'


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
