import yaml
import pytest
import json
from v1.routes.gateway import validate_upstream
from tests.testutils import trimleft
from unittest import mock

def test_local_host(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.mytest", "another"]
          routes:
          - name: route-1
            hosts: [ myapi.cluster.local ]
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
