from os import environ
from patterns.eval import evaluate_pattern
import yaml

def test_service_r1(client):
    context = {
        'service_name': 'LAB-MIN-CITZ-MY-SERVICE',
        'gateway': 'gw-xxx',
        'upstream_uri': 'https://app-service-r1.example.com',
        'ap_allow_list': 'ap-01.example.com',
        'route_host': 'ap-02.example.com',
        'route_path': '/LAB/MIN/CITZ/MY-SERVICE',
    }
    
    response = evaluate_pattern('sdx-service-r1', context)
    print(response)
    yaml_documents_iter = yaml.load_all(response, Loader=yaml.FullLoader)
    doc = next(yaml_documents_iter)
    assert doc['services'][0]["name"] == context['service_name']

def test_application_r1(client):
    context = {
        'service_name': 'REQ-0001-LAB-MIN-CITZ-MY-UI',
        'gateway': 'gw-xxx',
        'upstream_uri': 'https://ap-02.example.com',
        'route_host': 'ap-01.example.com',
        'route_path': '/LAB/MIN/CITZ/OTHER-SERVICE',
    }

    response = evaluate_pattern('sdx-application-r1', context)
    print(response)
    yaml_documents_iter = yaml.load_all(response, Loader=yaml.FullLoader)
    doc = next(yaml_documents_iter)
    assert doc['services'][0]["name"] == context['service_name']

