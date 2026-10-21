import json
import pytest
from unittest import mock
from clients.kong import get_records

KONG_ADMIN_API_URL = 'http://dp-admin-cache'


def _response(status_code, body):
    response = mock.Mock()
    response.status_code = status_code
    response.text = json.dumps(body)
    response.json.return_value = body
    return response


@pytest.fixture(autouse=True)
def kong_admin_api_url(monkeypatch):
    monkeypatch.setenv('KONG_ADMIN_API_URL', KONG_ADMIN_API_URL)


@mock.patch('clients.kong.requests.get')
def test_returns_records(mock_get):
    mock_get.return_value = _response(200, {"data": [{"name": "route-1"}], "next": None})

    assert get_records('routes') == [{"name": "route-1"}]
    mock_get.assert_called_once_with(KONG_ADMIN_API_URL + '/routes', timeout=mock.ANY)


@mock.patch('clients.kong.requests.get')
def test_follows_pagination(mock_get):
    mock_get.side_effect = [
        _response(200, {"data": [{"name": "route-1"}], "next": "/routes?offset=abc"}),
        _response(200, {"data": [{"name": "route-2"}], "next": None}),
    ]

    assert get_records('routes') == [{"name": "route-1"}, {"name": "route-2"}]
    assert mock_get.call_args_list[1] == mock.call(KONG_ADMIN_API_URL + '/routes?offset=abc', timeout=mock.ANY)


@pytest.mark.parametrize("record_type", ['certificates', 'snis'])
@mock.patch('clients.kong.requests.get')
def test_empty_list_is_valid(mock_get, record_type):
    # Certificates and SNIs only exist for custom domains, so an empty list is legitimate
    mock_get.return_value = _response(200, {"data": [], "next": None})

    assert get_records(record_type) == []


@pytest.mark.parametrize("status_code", [500, 503, 404])
@mock.patch('clients.kong.requests.get')
def test_non_2xx_response_raises(mock_get, status_code):
    # e.g. the DP admin cache returns 503 when the data plane has no config loaded
    mock_get.return_value = _response(status_code, {"message": "Service Unavailable: no config loaded"})

    with pytest.raises(RuntimeError, match="HTTP %s" % status_code):
        get_records('routes')


@mock.patch('clients.kong.requests.get')
def test_body_without_data_list_raises(mock_get):
    mock_get.return_value = _response(200, {"message": "unexpected"})

    with pytest.raises(RuntimeError, match="no data list"):
        get_records('routes')


def test_invalid_record_type_raises():
    with pytest.raises(ValueError):
        get_records('services')
