import pytest
from app import _get_certificate_for_host
from conftest import SAMPLE_CERT, SAMPLE_KEY

def test_get_certificate_standard_domain():
    """Test that standard domains return default cert configuration"""
    host = "api.gov.bc.ca"
    namespace = "test-ns"
    cert_snis = []
    certs = []

    cert, serial_number = _get_certificate_for_host(host, namespace, cert_snis, certs)
    assert cert is None
    assert serial_number is None

def test_get_certificate_custom_domain_found():
    """Test successful custom domain certificate lookup"""
    host = "test.custom.gov.bc.ca"
    namespace = "test-ns"
    cert_id = "41d14845-669f-4dcd-aff2-926fb32a4b25"
    cert_serial_number = "1"
    
    certs = [{
        "id": cert_id,
        "cert": SAMPLE_CERT,
        "created_at": 1731713874,
        "tags": ["ns.test-ns"],
        "key": SAMPLE_KEY
    }]
    
    cert_snis = [{
        "name": "test.custom.gov.bc.ca",
        "id": "79009c9e-0f4d-40b5-9707-bf2fe9f50502",
        "created_at": 1731713874,
        "certificate": cert_id,
        "tags": ["ns.test-ns"]
    }]

    cert, returned_serial_number = _get_certificate_for_host(host, namespace, cert_snis, certs)
    assert cert is not None
    assert returned_serial_number == cert_serial_number
    assert cert["snis"] == [host]

def test_get_certificate_custom_domain_sni_not_found():
    """Test custom domain with no matching certificate"""
    host = "missing.custom.gov.bc.ca"
    namespace = "test-ns"
    cert_snis = [{
        "name": "other.custom.gov.bc.ca",
        "certificate": "some-cert-id"
    }]
    certs = []

    with pytest.raises(Exception) as exc_info:
        _get_certificate_for_host(host, namespace, cert_snis, certs)
    assert str(exc_info.value) == f"Certificate not found for host {host}"

def test_get_certificate_missing_cert():
    """Test when SNI references a non-existent certificate"""
    host = "test.custom.gov.bc.ca"
    namespace = "test-ns"
    cert_id = "non-existent-cert"
    
    cert_snis = [{
        "name": host,
        "certificate": cert_id
    }]
    certs = []  # Empty certs list, so cert won't be found

    with pytest.raises(Exception) as exc_info:
        _get_certificate_for_host(host, namespace, cert_snis, certs)
    assert str(exc_info.value) == f"Certificate not found for id {cert_id}"

def test_get_certificate_empty_cert_snis():
    """Test custom domain with empty cert_snis"""
    host = "test.custom.gov.bc.ca"
    namespace = "test-ns"
    cert_snis = []
    certs = []

    with pytest.raises(Exception) as exc_info:
        _get_certificate_for_host(host, namespace, cert_snis, certs)
    assert str(exc_info.value) == f"Certificate SNI not found for host {host}"