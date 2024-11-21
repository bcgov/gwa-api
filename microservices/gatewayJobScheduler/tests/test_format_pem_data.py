from app import _format_pem_data

def test_format_pem_data_no_indent():
    single_line = "-----BEGIN CERTIFICATE-----\nABC123\n-----END CERTIFICATE-----"
    expected = "-----BEGIN CERTIFICATE-----\nABC123\n-----END CERTIFICATE-----"
    assert _format_pem_data(single_line, indent=0) == expected

def test_format_pem_data_with_indent_8():
    single_line = "-----BEGIN CERTIFICATE-----\nABC123\n-----END CERTIFICATE-----"
    expected = "        -----BEGIN CERTIFICATE-----\n        ABC123\n        -----END CERTIFICATE-----"
    assert _format_pem_data(single_line, indent=8) == expected 