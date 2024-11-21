from app import _is_host_custom_domain

def test_standard_domains():
    assert not _is_host_custom_domain("api.gov.bc.ca")
    assert not _is_host_custom_domain("test.api.gov.bc.ca")
    assert not _is_host_custom_domain("test.apps.gov.bc.ca")
    assert not _is_host_custom_domain("test.cluster.local")

def test_custom_domains():
    assert _is_host_custom_domain("custom.domain.com")
    assert _is_host_custom_domain("test.custom.gov.bc.ca") 