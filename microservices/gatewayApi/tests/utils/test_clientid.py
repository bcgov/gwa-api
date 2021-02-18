import re

from utils.clientid import client_id_valid, generate_client_id

def test_client_id_allowed():
    assert client_id_valid('testns', 'sa-testns-00000') == False
    assert client_id_valid('testns', 'xsa-testns-00000') == False
    assert client_id_valid('testns', 'sa-testns-dev-00000') == False
    assert client_id_valid('testns', 'sa-testns-dev-123456789') == False
    assert client_id_valid('testns', 'sa-testns-dev-1234567890') == False
    assert client_id_valid('testns', 'sa-testns-dev-12345678901') == False
    assert client_id_valid('testns-dev', 'sa-testns-dev-1234567890') == True

    assert client_id_valid('testns', generate_client_id('testns')) == True
