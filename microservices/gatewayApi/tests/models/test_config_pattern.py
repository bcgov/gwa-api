import json
from os import environ
from patterns.eval import evaluate_pattern
import yaml
from v2.models.gateway_config_pattern import GatewayConfigPattern

def test_model_r1(client):
    context = {
        'ns_qualifier': 'all',
        'pattern': 'sdx-service-r1',
        'service_name': 'LAB-MIN-CITZ-MY-SERVICE',
        'gateway': 'gw-xxx',
        'upstream_uri': 'https://app-service-r1.example.com',
        'mtls_allow_list': 'ap-01.example.com',
        'route_host': 'ap-02.example.com',
        'route_path': '/LAB/MIN/CITZ/MY-SERVICE',
        'consumer_uri': '',
        'consumer_client_id': '',
        'openid_issuer': '',
        'openid_audience': '',
        'openid_scope': '',
    }
    
    gw_pattern_context = GatewayConfigPattern (context)
    # gw_pattern_context.set_gateway(namespace)

    response = gw_pattern_context.get_config_file()

    print(response)
    yaml_documents_iter = yaml.load_all(response, Loader=yaml.FullLoader)
    doc = next(yaml_documents_iter)
    assert doc['services'][0]["name"] == context['service_name']

def test_model_keys_r1(client):
    public_key_pem = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzvYpY1k1k0kP7vV1X1JHqz
bX5+5b0F6v9vQ1ZlZ5sX6Fz3Yx8u5m2K1v1ZlZ5sX6Fz3Yx8u5m2K1v1ZlZ5sX6Fz3Yx8u
-----END PUBLIC KEY-----"""

    context = {
        'ns_qualifier': 'all',
        'pattern': 'sdx-keys-r1',
        'gateway': 'gw-xxx',
        'key_name': 'key-123',
        'kid': 'key-123-kid',
        'public_key_pem': public_key_pem,
    }
    
    gw_pattern_context = GatewayConfigPattern (context)
    gw_pattern_context.set_gateway('gw-yyy')

    response = gw_pattern_context.get_config_file()

    print(response)
    yaml_documents_iter = yaml.load_all(response, Loader=yaml.FullLoader)
    doc = next(yaml_documents_iter)
    assert doc['keys'][0]["name"] == context['key_name']
    assert doc['keys'][0]["tags"][0] == "ns.gw-yyy.all"
