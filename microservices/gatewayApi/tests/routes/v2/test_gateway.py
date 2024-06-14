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
