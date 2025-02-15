from clients.deck import convert_to_kong3
import pytest

# Test configurations
CONFIG_REGEX_FAIL = {
    "_format_version": "2.1",
    "services": [{
        "name": "example-service",
        "url": "http://example.com",
        "routes": [{
            "name": "example-route",
            "paths": ["/example*"]
        }]
    }]
}

CONFIG_REGEX_PASS = {
    "_format_version": "2.1",
    "services": [{
        "name": "example-service",
        "url": "http://example.com",
        "routes": [{
            "name": "example-route",
            "paths": ["~/example*"]
        }]
    }]
}

CONFIG_NO_REGEX_PASS = {
    "_format_version": "2.1",
    "services": [{
        "name": "example-service",
        "url": "http://example.com",
        "routes": [{
            "name": "example-route",
            "paths": ["/example"]
        }]
    }]
}

def test_convert_regex_fail():
    """Test that configuration with regex without tilde fails"""
    is_compatible, message, converted = convert_to_kong3(CONFIG_REGEX_FAIL)
    assert not is_compatible
    assert "unsupported routes' paths format with Kong version 3.0" in message
    assert converted is not None

def test_convert_regex_pass():
    """Test that configuration with proper regex tilde passes"""
    is_compatible, message, converted = convert_to_kong3(CONFIG_REGEX_PASS)
    assert is_compatible
    assert converted is not None

def test_convert_no_regex_pass():
    """Test that configuration without regex passes"""
    is_compatible, message, converted = convert_to_kong3(CONFIG_NO_REGEX_PASS)
    assert is_compatible
    assert converted is not None 