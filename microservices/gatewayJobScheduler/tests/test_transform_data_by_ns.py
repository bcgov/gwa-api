import json
from unittest import mock
from app import transform_data_by_ns

def test_happy_transform_data_by_ns():
    with mock.patch('clients.namespace.admin_api') as mock_admin_api:
        set_mock_admin_api_response(mock_admin_api)

        data = [
            {
                "name": "route-1",
                "tags": [ "ns.ns1"],
                "hosts": [
                    "host-1"
                ]
            }
        ]
        assert json.dumps(transform_data_by_ns(data)) == '{"ns1": [{"name": "wild-ns-ns1-host-1", "selectTag": "ns.ns1", "host": "host-1", "sessionCookieEnabled": false, "dataClass": null, "dataPlane": "test-dp"}]}'

def test_happy_transform_data_by_ns_with_override_session_cookie():
    with mock.patch('clients.namespace.admin_api') as mock_admin_api:
        set_mock_admin_api_response(mock_admin_api)

        data = [
            {
                "name": "route-1",
                "tags": [ "ns.ns1", "aps.route.session.cookie.enabled"],
                "hosts": [
                    "host-1"
                ]
            }
        ]
        assert json.dumps(transform_data_by_ns(data)) == '{"ns1": [{"name": "wild-ns-ns1-host-1", "selectTag": "ns.ns1", "host": "host-1", "sessionCookieEnabled": true, "dataClass": null, "dataPlane": "test-dp"}]}'

def test_happy_transform_data_by_ns_with_override_data_plane():
    with mock.patch('clients.namespace.admin_api') as mock_admin_api:
        set_mock_admin_api_response(mock_admin_api)

        data = [
            {
                "name": "route-1",
                "tags": [ "ns.ns1", "aps.route.dataclass.high"],
                "hosts": [
                    "host-1"
                ]
            }
        ]
        assert json.dumps(transform_data_by_ns(data)) == '{"ns1": [{"name": "wild-ns-ns1-host-1", "selectTag": "ns.ns1", "host": "host-1", "sessionCookieEnabled": false, "dataClass": "high", "dataPlane": "test-dp"}]}'

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
