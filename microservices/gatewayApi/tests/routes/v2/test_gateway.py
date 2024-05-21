import yaml
import pytest
import json
from v1.routes.gateway import validate_upstream
from tests.testutils import trimleft
from unittest import mock

def test_happy_gateway_call(client):
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
