from routers.routes import convert_to_kong2

def test_convert_to_kong2_none():
    """Test conversion with None input"""
    result = convert_to_kong2(None)
    assert result is None

def test_convert_to_kong2_tilde():
    """Test conversion removes tildes"""
    kong3_config = {
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
    
    result = convert_to_kong2(kong3_config)
    assert result["_format_version"] == "2.1"
    assert result["services"][0]["routes"][0]["paths"][0] == "/example*"

def test_convert_to_kong2_no_tilde():
    """Test conversion with no tildes"""
    kong3_config = {
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
    
    result = convert_to_kong2(kong3_config)
    assert result["_format_version"] == "2.1"
    assert result["services"][0]["routes"][0]["paths"][0] == "/example" 