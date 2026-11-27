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


CERT_UPDATE_DIFF = """\
updating certificate 8fc131ef-9752-43a4-ba70-eb10ba442d4e
-  "key": "-----BEGIN PRIVATE KEY-----\\nOLDPRIVATEKEYDATA\\n-----END PRIVATE KEY-----",
+  "key": "-----BEGIN PRIVATE KEY-----\\nNEWPRIVATEKEYDATA\\n-----END PRIVATE KEY-----",
-  "key_alt": "-----BEGIN RSA PRIVATE KEY-----\\nOLDALTKEYDATA\\n-----END RSA PRIVATE KEY-----",
+  "key_alt": "-----BEGIN OPENSSH PRIVATE KEY-----\\nNEWALTKEYDATA\\n-----END OPENSSH PRIVATE KEY-----",
   "cert": "-----BEGIN CERTIFICATE-----\\nMIIBCERTBODY\\n-----END CERTIFICATE-----"
"""

PUBLISH_CONFIG = '''
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


class _DeckOutput:
    def __init__(self, output):
        self.output = output

    def decode(self, encoding):
        return self.output


class _DeckProcess:
    def __init__(self, output, returncode):
        self.output = output
        self.returncode = returncode

    def communicate(self):
        return _DeckOutput(self.output), None


def _gateway_view(view):
    seen = set()
    while view not in seen:
        seen.add(view)
        if "Popen" in getattr(view, "__globals__", {}):
            return view
        wrapped = getattr(view, "__wrapped__", None)
        if wrapped is None:
            break
        view = wrapped
    raise AssertionError("gateway view does not bind Popen")


def _patch_deck(mocker, app, calls):
    pending = list(calls)

    def popen(*args, **kwargs):
        output, returncode = pending.pop(0)
        return _DeckProcess(output, returncode)

    # Decorators wrap the route, and the app fixture may drop the module from
    # sys.modules. Patch the Popen name the live function closes over.
    view = _gateway_view(app.view_functions["gwa_v2.write_config"])
    mocker.patch.dict(view.__globals__, {"Popen": popen})


def _assert_certificate_diff_masked(results):
    assert "BEGIN PRIVATE KEY" not in results
    assert "BEGIN RSA PRIVATE KEY" not in results
    assert "BEGIN OPENSSH PRIVATE KEY" not in results
    assert "OLDPRIVATEKEYDATA" not in results
    assert "NEWPRIVATEKEYDATA" not in results
    assert "OLDALTKEYDATA" not in results
    assert "NEWALTKEYDATA" not in results
    assert "BEGIN CERTIFICATE" in results
    assert "MIIBCERTBODY" in results


def test_publish_masks_certificate_update_diff(client, app, mocker):
    _patch_deck(mocker, app, [(CERT_UPDATE_DIFF, 0)] * 4)
    warned = mocker.patch.object(app.logger, "warn")

    dry_run = client.put(
        "/v2/namespaces/mytest/gateway",
        json={"configFile": PUBLISH_CONFIG, "dryRun": True},
    )
    assert dry_run.status_code == 200
    assert dry_run.json["message"] == "Dry-run.  No changes applied."
    _assert_certificate_diff_masked(dry_run.json["results"])

    sync = client.put(
        "/v2/namespaces/mytest/gateway",
        json={"configFile": PUBLISH_CONFIG, "dryRun": False},
    )
    assert sync.status_code == 200
    assert sync.json["message"] == "Sync successful."
    _assert_certificate_diff_masked(sync.json["results"])
    assert warned.call_count == 0

    _patch_deck(mocker, app, [("validate ok", 0), (CERT_UPDATE_DIFF, 1)])
    failed = client.put(
        "/v2/namespaces/mytest/gateway",
        json={"configFile": PUBLISH_CONFIG, "dryRun": False},
    )
    assert failed.status_code == 400
    assert failed.json["error"] == "Sync Failed."
    _assert_certificate_diff_masked(failed.json["results"])
    assert warned.call_count == 1
    _assert_certificate_diff_masked(warned.call_args.args[0])

