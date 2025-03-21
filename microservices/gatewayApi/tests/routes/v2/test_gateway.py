import yaml
import pytest
import json
from v1.routes.gateway import validate_upstream
from tests.testutils import trimleft
from unittest import mock

def test_happy_dryrun_gateway_call(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.mytest", "another"]
          routes:
          - name: route-1
            hosts: [ myapi.api.gov.bc.ca ]
            tags: ["ns.mytest", "another2"]
            plugins:
            - name: acl-auth
              tags: ["ns.mytest"]
        '''

    data={
        "configFile": configFile,
        "dryRun": True
    }
    response = client.put('/v2/namespaces/mytest/gateway', json=data)
    assert response.status_code == 200
    assert json.dumps(response.json) == '{"message": "Dry-run.  No changes applied.", "results": "Deck reported no changes"}'

def test_happy_dryrun_with_qualifier_gateway_call(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.mytest.dev", "another"]
          routes:
          - name: route-1
            hosts: [ myapi.api.gov.bc.ca ]
            tags: ["ns.mytest.dev", "another2"]
            plugins:
            - name: acl-auth
              tags: ["ns.mytest.dev"]
        '''

    data={
        "configFile": configFile,
        "dryRun": True
    }
    response = client.put('/v2/namespaces/mytest/gateway', json=data)
    assert response.status_code == 200
    assert json.dumps(response.json) == '{"message": "Dry-run.  No changes applied.", "results": "Deck reported no changes"}'


def test_happy_sync_gateway_call(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.mytest", "another"]
          routes:
          - name: route-1
            hosts: [ myapi.api.gov.bc.ca ]
            tags: ["ns.mytest", "another2"]
            plugins:
            - name: acl-auth
              tags: ["ns.mytest"]
        '''

    data={
        "configFile": configFile,
        "dryRun": False
    }
    response = client.put('/v2/namespaces/mytest/gateway', json=data)
    assert response.status_code == 200
    assert json.dumps(response.json) == '{"message": "Sync successful.", "results": "Deck reported no changes"}'

def test_happy_with_session_cookie_gateway_call(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.sescookie.dev", "another"]
          routes:
          - name: route-1
            hosts: [ myapi.api.gov.bc.ca ]
            tags: ["ns.sescookie.dev", "aps.route.session.cookie.enabled"]
            plugins:
            - name: acl-auth
              tags: ["ns.sescookie.dev"]
        '''

    data={
        "configFile": configFile,
        "dryRun": False
    }
    response = client.put('/v2/namespaces/sescookie/gateway', json=data)
    assert response.status_code == 200
    assert json.dumps(response.json) == '{"message": "Sync successful.", "results": "Deck reported no changes"}'

def test_happy_with_data_class_gateway_call(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.dclass.dev", "aps.route.dataclass.high"]
          routes:
          - name: route-1
            hosts: [ myapi.api.gov.bc.ca ]
            tags: ["ns.dclass.dev"]
            plugins:
            - name: acl-auth
              tags: ["ns.dclass.dev"]
        '''

    data={
        "configFile": configFile,
        "dryRun": False
    }
    response = client.put('/v2/namespaces/dclass/gateway', json=data)
    assert response.status_code == 200
    assert json.dumps(response.json) == '{"message": "Sync successful.", "results": "Deck reported no changes"}'

def test_happy_with_custom_domain_gateway_call(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          ca_certificates: [ "0000-0000-0000-0000" ]
          certificate: "41d14845-669f-4dcd-aff2-926fb32a4b25"
          tags: ["ns.customcert"]
          routes:
          - name: route-1
            hosts: [ test.custom.gov.bc.ca ]
            tags: ["ns.customcert"]
            plugins:
            - name: acl-auth
              tags: ["ns.customcert"]
        '''

    data={
        "configFile": configFile,
        "dryRun": False
    }
    response = client.put('/v2/namespaces/customcert/gateway', json=data)
    assert response.status_code == 200
    assert json.dumps(response.json) == '{"message": "Sync successful.", "results": "Deck reported no changes"}'

def test_success_mtls_reference(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          ca_certificates: [ "0000-0000-0000-0000" ]
          certificate: "8fc131ef-9752-43a4-ba70-eb10ba442d4e"
          tags: ["ns.mytest", "another"]
          routes:
          - name: route-1
            hosts: [ my-service.api.gov.bc.ca ]
            tags: ["ns.mytest", "another2"]
        '''

    data={
        "configFile": configFile,
        "dryRun": False
    }
    response = client.put('/v2/namespaces/mytest/gateway', json=data)
    assert response.status_code == 200
    assert json.dumps(response.json) == '{"message": "Sync successful.", "results": "Deck reported no changes"}'

# def test_kong3_compatibility_warning(client):
#     """Test that Kong 3 incompatible config generates warning"""
#     configFile = '''
#         services:
#         - name: my-service
#           host: myupstream.local
#           tags: ["ns.mytest", "another"]
#           routes:
#           - name: route-1
#             hosts: [ myapi.api.gov.bc.ca ]
#             paths: [ "/path*" ]
#             tags: ["ns.mytest", "another2"]
#           - name: route-2
#             hosts: [ myapi2.api.gov.bc.ca ]
#             paths: [ "/other*" ]
#             tags: ["ns.mytest", "another2"]
#         '''

#     data = {
#         "configFile": configFile,
#         "dryRun": False
#     }
#     response = client.put('/v2/namespaces/mytest/gateway', json=data)
#     assert response.status_code == 200
#     response_data = response.json
#     assert response_data["message"] == "Sync successful."
    
#     # Verify warning message and failed routes are in results
#     results = response_data["results"]
#     assert "Kong 3 incompatible routes found" in results
#     assert "route-1" in results
#     assert "route-2" in results
#     # Routes should only be listed once even if multiple incompatible paths
#     assert results.count("route-1") == 1
