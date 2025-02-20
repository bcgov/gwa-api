from unittest import mock
import socket
import requests
from routers.routes import build_url, default, clean_host
import pytest

@pytest.fixture
def service_payload():
    return {
        "services": [{"id": "service-id", "name": "test-service", "host": "test-service.svc"}],
        "routes": [{"service": {"id": "service-id"}, "hosts": ["test-service.svc"], "preserve_host": True}],
        "conf": {"enabled": True, "baseUrl": "http://example.com"}
    }

def test_service_status_up(client, service_payload):
    with mock.patch("socket.gethostbyname", return_value="1.1.1.1"):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200

            response = client.get("/namespaces/test-ns/service-status", json=service_payload)
            assert response.status_code == 200
            assert response.json()['services_status'][0]['status'] == 'UP'
            assert response.json()['services_status'][0]['reason'] == '200 Response'

def test_service_status_dns_failure(client, service_payload):
    with mock.patch("socket.gethostbyname", side_effect=socket.gaierror):
        response = client.get("/namespaces/test-ns/service-status", json=service_payload)
        assert response.status_code == 200
        assert response.json()['services_status'][0]['status'] == 'DOWN'
        assert response.json()['services_status'][0]['reason'] == 'DNS'

def test_service_status_timeout(client, service_payload):
    with mock.patch("socket.gethostbyname", return_value="1.1.1.1"):
        with mock.patch("requests.get", side_effect=requests.exceptions.Timeout):
            response = client.get("/namespaces/test-ns/service-status", json=service_payload)
            assert response.status_code == 200
            assert response.json()['services_status'][0]['status'] == 'DOWN'
            assert response.json()['services_status'][0]['reason'] == 'TIMEOUT'

def test_service_status_connection_error(client, service_payload):
    with mock.patch("socket.gethostbyname", return_value="1.1.1.1"):
        with mock.patch("requests.get", side_effect=requests.exceptions.ConnectionError):
            response = client.get("/namespaces/test-ns/service-status", json=service_payload)
            assert response.status_code == 200
            assert response.json()['services_status'][0]['status'] == 'DOWN'
            assert response.json()['services_status'][0]['reason'] == 'CONNECTION'

def test_service_status_custom_host(client, service_payload):
    custom_host_payload = service_payload.copy()
    custom_host_payload["routes"][0]["hosts"] = ["custom-host"]
    
    with mock.patch("socket.gethostbyname", return_value="1.1.1.1"):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            response = client.get("/namespaces/test-ns/service-status", json=custom_host_payload)
            assert response.status_code == 200
            assert response.json()['services_status'][0]['status'] == 'UP'
            assert response.json()['services_status'][0]['reason'] == '200 Response'
            assert response.json()['services_status'][0]['host'] == 'custom-host'

def test_build_url():
    service = {
        "host": "example.com",
        "protocol": "http",
        "port": 80,
        "path": "/service"
    }

    url = build_url(service)
    assert url == "http://example.com:80/service"

    service_no_port = { "host": "example.com", "protocol": "http", "path": "/service" }
    url = build_url(service_no_port)
    assert url == "http://example.com:80/service"

    service_https = { "host": "example.com", "protocol": "https", "port": 443, "path": "/secure-service" }
    url = build_url(service_https)
    assert url == "https://example.com:443/secure-service"

def test_default():
    service = {"host": "example.com", "protocol": "http"}

    assert default(service, "host", "default.com") == "example.com"
    
    assert default(service, "port", 8080) == 8080

def test_clean_host():
    conf_enabled = {"enabled": True, "baseUrl": "http://example.com"}
    conf_disabled = {"enabled": False, "baseUrl": "http://example.com"}
    
    host = "test-data-gov-bc-ca.example.com"

    cleaned_host = clean_host(host, conf_enabled)
    assert cleaned_host == "test.data.example.com"

    cleaned_host = clean_host(host, conf_disabled)
    assert cleaned_host == "test-data-gov-bc-ca.example.com"
