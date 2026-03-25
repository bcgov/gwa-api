import yaml
import pytest
import json
from v1.routes.gateway import validate_upstream
from tests.testutils import trimleft
from unittest import mock


def test_success_sdx_call_empty(client):
    data={
        "configFile": '---',
        "dryRun": False
    }
    response = client.put('/v2/namespaces/sdx01/gateway', json=data)
    assert response.status_code == 200
    assert json.dumps(response.json) == '{"message": "Sync successful.", "results": "Deck reported no changes"}'

def test_success_sdx_call(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.sdx01.qualifier"]
          routes:
          - name: route-1
            hosts: [ sdx01.servers.sdx]
            tags: ["ns.sdx01.qualifier"]
            plugins:
            - name: acl-auth
              tags: ["ns.sdx01.qualifier"]
        '''
        
    data={
        "configFile": configFile,
        "dryRun": False
    }
    response = client.put('/v2/namespaces/sdx01/gateway', json=data)
    assert response.status_code == 200
    assert json.dumps(response.json) == '{"message": "Sync successful.", "results": "Deck reported no changes"}'
