import yaml
import pytest
import json
from v1.routes.gateway import validate_upstream
from tests.testutils import trimleft
from unittest import mock

def test_error_call_with_missing_config(client):
    data={
        "dryRun": True
    }
    response = client.put('/v2/namespaces/mytest/gateway', json=data)
    assert response.status_code == 400
    assert json.dumps(response.json) == '{"error": "Missing input"}'


def test_error_call_with_empty_config(client):
    data={
        "configFile": '',
        "dryRun": True
    }
    response = client.put('/v2/namespaces/mytest/gateway', json=data)
    assert response.status_code == 400
    assert json.dumps(response.json) == '{"error": "Missing input"}'

def test_success_call_with_empty_document(client):
    data={
        "configFile": '---',
        "dryRun": True
    }
    response = client.put('/v2/namespaces/mytest/gateway', json=data)
    assert response.status_code == 200
    assert json.dumps(response.json) == '{"message": "Dry-run.  No changes applied.", "results": "Deck reported no changes"}'
