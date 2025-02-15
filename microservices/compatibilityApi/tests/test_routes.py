from fastapi.testclient import TestClient
from app import create_app

# Create the FastAPI app
app = create_app()
# Create the test client
client = TestClient(app)

def test_validate_kong3_compatibility_fail():
    """Test validation of Kong 2.x config with unsupported regex"""
    response = client.post("/config", json={
        "_format_version": "2.1",
        "services": [{
            "name": "example-service",
            "url": "http://example.com",
            "routes": [{
                "name": "example-route",
                "paths": ["/example*"]
            }]
        }]
    })
    assert response.status_code == 200
    data = response.json()
    assert not data["kong3_compatible"]
    assert "unsupported routes' paths format with Kong version 3.0" in data["conversion_output"]

def test_validate_kong3_compatibility_pass():
    """Test validation of Kong 3.x compatible config"""
    response = client.post("/config", json={
        "_format_version": "2.1",
        "services": [{
            "name": "example-service",
            "url": "http://example.com",
            "routes": [{
                "name": "example-route",
                "paths": ["~/example*"]
            }]
        }]
    })
    assert response.status_code == 200
    data = response.json()
    assert data["kong3_compatible"]

def test_validate_no_regex_pass():
    """Test validation of config without regex"""
    response = client.post("/config", json={
        "_format_version": "2.1",
        "services": [{
            "name": "example-service",
            "url": "http://example.com",
            "routes": [{
                "name": "example-route",
                "paths": ["/example"]
            }]
        }]
    })
    assert response.status_code == 200
    data = response.json()
    assert data["kong3_compatible"] 