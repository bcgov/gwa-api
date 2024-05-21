import yaml
import pytest
import json
from v1.routes.gateway import validate_upstream
from tests.testutils import trimleft
from unittest import mock

def test_missing_required_tag(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.mytest-invalid", "another"]
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
    assert response.status_code == 400
    assert json.dumps(response.json) == '{"error": "Validation Errors:\\n.services.my-service missing required tag ns.mytest\\n.services.my-service invalid ns tag ns.mytest-invalid"}'

def test_invalid_host(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.mytest", "another"]
          routes:
          - name: route-1
            hosts: [ myapi.invalid.site ]
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
    assert response.status_code == 400
    assert json.dumps(response.json) == '{"error": "Validation Errors:\\nHost invalid: route-1 myapi.invalid.site.  Route hosts must end with one of [.api.gov.bc.ca] for this namespace."}'

