from clients.deck import convert_to_kong3
import pytest
import yaml

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

# Mock deck responses
def mock_deck_fail(args):
    """Mock deck response for failing regex case"""
    # Get output file path from args
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
    
    # Write the converted config
    with open(output_file, 'w') as f:
        yaml.dump(converted, f)
    
    return 0, """
Warning: unsupported routes' paths format with Kong version 3.0
Converting configuration file...
Wrote converted configuration to output file
"""

def mock_deck_pass(args):
    """Mock deck response for passing cases"""
    # Get input and output file paths
    input_file = args[args.index("--input-file") + 1]
    output_file = args[args.index("--output-file") + 1]
    
    # Read the input config to determine if it's a regex case
    with open(input_file, 'r') as f:
        input_config = yaml.safe_load(f)
    
    # Check if the input has a tilde path
    has_tilde = any(path.startswith('~') for path in input_config['services'][0]['routes'][0]['paths'])
    
    # Create mock converted output
    converted = {
        "_format_version": "3.0",
        "services": [{
            "name": "example-service",
            "host": "example.com",
            "port": 80,
            "protocol": "http",
            "routes": [{
                "name": "example-route",
                "paths": ["~/example*"] if has_tilde else ["/example"]
            }]
        }]
    }
    
    # Write mock converted config to the output file
    with open(output_file, 'w') as f:
        yaml.dump(converted, f)
    
    return 0, "Converting configuration file...\nWrote converted configuration to output file"

def test_convert_regex_fail():
    """Test that configuration with regex without tilde fails"""
    is_compatible, message, converted = convert_to_kong3(CONFIG_REGEX_FAIL, deck_runner=mock_deck_fail)
    assert not is_compatible
    assert "unsupported routes' paths format with Kong version 3.0" in message
    assert converted is not None

def test_convert_regex_pass():
    """Test that configuration with proper regex tilde passes"""
    is_compatible, message, converted = convert_to_kong3(CONFIG_REGEX_PASS, deck_runner=mock_deck_pass)
    assert is_compatible
    assert converted is not None
    assert converted["services"][0]["routes"][0]["paths"][0].startswith("~")

def test_convert_no_regex_pass():
    """Test that configuration without regex passes"""
    is_compatible, message, converted = convert_to_kong3(CONFIG_NO_REGEX_PASS, deck_runner=mock_deck_pass)
    assert is_compatible
    assert converted is not None
    assert not converted["services"][0]["routes"][0]["paths"][0].startswith("~") 