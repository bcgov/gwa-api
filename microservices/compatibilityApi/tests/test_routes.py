from fastapi.testclient import TestClient
from app import create_app
import pytest
from unittest.mock import patch
import yaml

# Create the FastAPI app
app = create_app()
# Create the test client
client = TestClient(app)

def test_validate_kong3_compatibility_fail():
    """Test validation of Kong 2.x config with unsupported regex"""
    with patch('clients.deck.run_deck_command') as mock_deck:
        # Mock the deck command to simulate a regex validation failure
        mock_deck.return_value = (0, "Warning: unsupported routes' paths format with Kong version 3.0")
        
        # Create a temporary file with converted config
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
                        "paths": ["~/example*"]
                    }]
                }]
            }
            with open(output_file, 'w') as f:
                yaml.dump(converted, f)
            return (0, "Warning: unsupported routes' paths format with Kong version 3.0")
            
        mock_deck.side_effect = mock_side_effect
        
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
    with patch('clients.deck.run_deck_command') as mock_deck:
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
                        "paths": ["~/example*"]
                    }]
                }]
            }
            with open(output_file, 'w') as f:
                yaml.dump(converted, f)
            return (0, "Converting configuration file...\nWrote converted configuration to output file")
            
        mock_deck.side_effect = mock_side_effect
        
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
    with patch('clients.deck.run_deck_command') as mock_deck:
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
                        "paths": ["/example"]
                    }]
                }]
            }
            with open(output_file, 'w') as f:
                yaml.dump(converted, f)
            return (0, "Converting configuration file...\nWrote converted configuration to output file")
            
        mock_deck.side_effect = mock_side_effect
        
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