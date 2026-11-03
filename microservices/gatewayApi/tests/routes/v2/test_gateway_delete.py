import yaml
import pytest
import json
from v1.routes.gateway import validate_upstream
from tests.testutils import trimleft
from unittest import mock

def test_happy_delete_gateway_call(client):

    response = client.delete('/v2/namespaces/mytest/gateway')
    assert response.status_code == 204

def test_happy_delete_with_qualifier_gateway_call(client):

    response = client.delete('/v2/namespaces/mytest/gateway/dev')
    assert response.status_code == 204

def test_delete_gateway_with_unconfigured_data_plane(client):

    response = client.delete('/v2/namespaces/unknowndp/gateway')
    assert response.status_code == 409
    body = response.get_json()
    assert body['error'] == 'Data Plane Not Configured'
    assert body['error_description'] == "Data plane 'not-configured-dp' is not configured"
    assert body['error_id']
