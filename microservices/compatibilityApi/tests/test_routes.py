from fastapi.testclient import TestClient
from app import create_app
import pytest
from unittest.mock import patch
import yaml

# Create the FastAPI app
app = create_app()
# Create the test client
client = TestClient(app)

# Define the mock at module level
def create_mock_side_effect(paths, warning=None):
    def mock_side_effect(args):
        output_file = args[args.index("--output-file") + 1]
        converted = {
            "_format_version": "3.0",
            "services": [{
                "name": "example-service",
                "host": "example.com",
                "port": 80,
                "protocol": "http",
                "routes": [{
                    "name": "example-route",
                    "paths": paths
                }]
            }]
        }
        with open(output_file, 'w') as f:
            yaml.dump(converted, f)
        return (0, warning or "Converting configuration file...\nWrote converted configuration to output file")
    return mock_side_effect

@patch('routers.routes.convert_to_kong3')
def test_validate_kong3_compatibility_fail(mock_convert):
    """Test validation of Kong 2.x config with unsupported regex"""
    mock_convert.return_value = (False, "", {
        "_format_version": "3.0",
        "services": [{
            "name": "example-service",
            "host": "example.com",
            "routes": [{
                "name": "example-route",
                "paths": ["~/example*"]
            }]
        }]
    })
    
    response = client.post("/configs", json={
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
    assert "WARNING: Kong 3 incompatible routes found" in data["message"]
    assert "example-route" in data["failed_routes"]
    assert data["kong3_output"]["services"][0]["routes"][0]["paths"][0].startswith("~")

@patch('routers.routes.convert_to_kong3')
def test_validate_kong3_compatibility_pass(mock_convert):
    """Test validation of Kong 3.x compatible config"""
    mock_convert.return_value = (True, "", {
        "_format_version": "3.0",
        "services": [{
            "name": "example-service",
            "host": "example.com",
            "routes": [{
                "name": "example-route",
                "paths": ["~/example*"]
            }]
        }]
    })
    
    response = client.post("/configs", json={
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
    assert "Gateway configuration is compatible with Kong 3" in data["message"]
    assert len(data["failed_routes"]) == 0

@patch('routers.routes.convert_to_kong3')  # Patch at the usage point
def test_validate_no_regex_pass(mock_convert):
    """Test validation of config without regex"""
    # Set up mock to return compatible result
    mock_convert.return_value = (
        True,
        "Converting configuration file...\nWrote converted configuration to output file",
        {
            "_format_version": "3.0",
            "services": [{
                "name": "example-service",
                "host": "example.com",
                "port": 80,
                "protocol": "http",
                "routes": [{
                    "name": "example-route",
                    "paths": ["/example"]
                }]
            }]
        }
    )
    
    response = client.post("/configs", json={
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