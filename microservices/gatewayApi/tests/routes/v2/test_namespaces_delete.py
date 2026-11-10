import pytest
from flask import g


@pytest.fixture
def ns_client(app, mocker):
    mocker.patch('v2.routes.namespaces.get_token', return_value={'access_token': 'pat'})

    # The mocked auth does not set a principal; delete_namespace reads it
    @app.before_request
    def set_principal():
        g.principal = {'preferred_username': 'tester'}
    return app.test_client()

def test_happy_delete_namespace_on_configured_data_plane(ns_client):

    response = ns_client.delete('/v2/namespaces/sdx01')
    assert response.status_code == 204

def test_delete_namespace_with_unconfigured_data_plane(ns_client):

    response = ns_client.delete('/v2/namespaces/unknowndp')
    assert response.status_code == 500
    body = response.get_json()
    assert body['error'] == 'Data Plane Not Configured'
    assert body['error_description'] == "Data plane 'not-configured-dp' is not configured"
    assert body['error_id']
