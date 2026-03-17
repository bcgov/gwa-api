import pytest
from auth.token import realm_base_url


def test_realm_base_url_without_trailing_slash():
    """serverUrl without trailing slash should produce a single slash before realms."""
    assert realm_base_url("http://keycloak:8080", "myrealm") == "http://keycloak:8080/realms/myrealm"


def test_realm_base_url_with_trailing_slash():
    """serverUrl with trailing slash should not produce a double slash before realms."""
    assert realm_base_url("http://keycloak:8080/", "myrealm") == "http://keycloak:8080/realms/myrealm"
