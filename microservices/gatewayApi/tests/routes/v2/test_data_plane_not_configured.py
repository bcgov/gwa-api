import pytest

# The "unknowndp" namespace's perm-data-plane is not in config/test.json

def assert_data_plane_not_configured(response):
    assert response.status_code == 409
    body = response.get_json()
    assert body['error'] == 'Data Plane Not Configured'
    assert body['error_description'] == "Data plane 'not-configured-dp' is not configured"
    assert body['error_id']

def test_publish_gateway_with_unconfigured_data_plane(client):
    data = {
        "configFile": "services: []",
        "dryRun": True
    }
    response = client.put('/v2/namespaces/unknowndp/gateway', json=data)
    assert_data_plane_not_configured(response)

def test_get_keys_with_unconfigured_data_plane(client, mocker):
    get_keys = mocker.patch("v2.routes.gw_keys.get_keys_and_key_sets")
    response = client.get('/v2/namespaces/unknowndp/keys')
    assert_data_plane_not_configured(response)
    get_keys.assert_not_called()

def test_get_resources_with_unconfigured_data_plane(client, mocker):
    get_resources = mocker.patch("v2.routes.gw_resources.get_tagged_resources_by_tag")
    response = client.get('/v2/namespaces/unknowndp/resources')
    assert_data_plane_not_configured(response)
    get_resources.assert_not_called()

def test_get_statuses_with_unconfigured_data_plane(client, mocker):
    mocker.patch("v2.routes.gw_status.get_services_by_ns", return_value=[])
    mocker.patch("v2.routes.gw_status.get_routes_by_ns", return_value=[])
    response = client.get('/v2/namespaces/unknowndp/services')
    assert_data_plane_not_configured(response)

def test_unexpected_error_includes_error_id(client, mocker):
    mocker.patch("v2.routes.gw_keys.get_keys_and_key_sets", side_effect=RuntimeError("boom"))
    response = client.get('/v2/namespaces/mytest/keys')
    assert response.status_code == 400
    body = response.get_json()
    assert body['error'] == 'Unexpected Error'
    assert body['error_id']
