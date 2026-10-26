"""Namespace cleanup regressions; downstream absence must not mask failures."""
from unittest.mock import Mock

import pytest
from flask import g


@pytest.fixture
def namespace_client(client, app, mocker):
    # The shared fixture bypasses authentication; supply its normal principal.
    @app.before_request
    def principal():
        g.principal = {'preferred_username': 'namespace-owner'}

    mocker.patch('v2.routes.namespaces.get_token', return_value={'access_token': 'pat'})
    return client


@pytest.mark.parametrize('namespace', ['mytest', 'sdx01'])
def test_delete_empty_namespace_and_repeat(namespace_client, namespace):
    # Empty decK state is valid for both a never-provisioned gateway and a
    # retry after its configuration was removed. The namespace remains authorized.
    for _ in range(2):
        response = namespace_client.delete('/v2/namespaces/' + namespace)
        assert response.status_code == 204


def test_namespace_sync_failure_is_not_success(namespace_client, mocker):
    process = Mock(returncode=1)
    process.communicate.return_value = (b'upstream unavailable', None)
    mocker.patch('v2.routes.namespaces.Popen', return_value=process)

    response = namespace_client.delete('/v2/namespaces/sdx01')

    assert response.status_code == 400
    assert response.get_json()['error'] == 'Sync Failed.'


def test_namespace_route_failure_is_not_success(namespace_client, mocker):
    mocker.patch('v2.routes.namespaces.requests.Session.put',
                 return_value=Mock(status_code=503, text='unavailable'))

    response = namespace_client.delete('/v2/namespaces/sdx01')

    assert response.status_code == 400
    assert response.get_json()['error'] == 'Partially failed.'
