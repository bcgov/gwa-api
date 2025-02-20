from utils.transforms import convert_to_kong2, is_path_regex_like, tag_routes

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

def test_is_path_regex_like():
    """Test regex path detection"""
    # Should detect regex patterns
    assert is_path_regex_like("/path*")
    assert is_path_regex_like("/path+")
    assert is_path_regex_like("/path?")
    assert is_path_regex_like("/path(test)")
    assert is_path_regex_like("/path[test]")
    assert is_path_regex_like("/path{test}")
    
    # Should not detect normal paths
    assert not is_path_regex_like("/simple/path")
    assert not is_path_regex_like("/path/with-hyphen")
    assert not is_path_regex_like("/path/with_underscore")
    assert not is_path_regex_like("/path/with.dot")
    assert not is_path_regex_like("/path/with~tilde")
    assert not is_path_regex_like("/path/with%20encoding")

def test_tag_routes_empty():
    """Test tagging with empty config"""
    config = {}
    tagged, failed = tag_routes(config)
    assert tagged == {}
    assert failed == []

def test_tag_routes_no_regex():
    """Test tagging with no regex paths"""
    config = {
        "services": [{
            "routes": [{
                "name": "simple-route",
                "paths": ["/simple/path"]
            }]
        }]
    }
    tagged, failed = tag_routes(config)
    assert "kong3=pass" not in tagged["services"][0]["routes"][0]["tags"]
    assert "kong3=fail" not in tagged["services"][0]["routes"][0]["tags"]
    assert failed == []

def test_tag_routes_with_tilde():
    """Test tagging with proper Kong 3 regex paths"""
    config = {
        "services": [{
            "routes": [{
                "name": "regex-route",
                "paths": ["~/path*", "~/other*"],
                "tags": ["existing-tag"]
            }]
        }]
    }
    tagged, failed = tag_routes(config)
    assert "kong3=pass" in tagged["services"][0]["routes"][0]["tags"]
    assert "existing-tag" in tagged["services"][0]["routes"][0]["tags"]
    assert failed == []

def test_tag_routes_without_tilde():
    """Test tagging with Kong 3 incompatible regex paths"""
    config = {
        "services": [{
            "routes": [{
                "name": "bad-regex-route",
                "paths": ["/path*", "~/other+"],
                "tags": ["existing-tag"]
            }]
        }]
    }
    tagged, failed = tag_routes(config)
    assert "kong3=fail" in tagged["services"][0]["routes"][0]["tags"]
    assert "existing-tag" in tagged["services"][0]["routes"][0]["tags"]
    assert failed == ["bad-regex-route"]

def test_tag_routes_cleans_existing():
    """Test that existing kong3 tags are cleaned"""
    config = {
        "services": [{
            "routes": [{
                "name": "route-1",
                "paths": ["/path*"],
                "tags": ["kong3=pass", "other-tag"]
            }]
        }]
    }
    tagged, failed = tag_routes(config)
    tags = tagged["services"][0]["routes"][0]["tags"]
    assert "kong3=pass" not in tags
    assert "kong3=fail" in tags
    assert "other-tag" in tags
    assert failed == ["route-1"] 