from unittest import mock
import datetime
from conftest import SAMPLE_CERT, SAMPLE_KEY, SAMPLE_CERT_FORMATTED, SAMPLE_KEY_FORMATTED

route_new_yaml = """
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: wild-ns-EXAMPLE-NS-abc.api.gov.bc.ca
  resourceVersion: ""
  annotations:
    haproxy.router.openshift.io/balance: random
    haproxy.router.openshift.io/disable_cookies: 'true'
    haproxy.router.openshift.io/timeout: 30m

  labels:
    aps-generated-by: "gwa-cli"
    aps-published-on: "2024.05-May.08"
    aps-namespace: "examplens"
    aps-select-tag: "ns.EXAMPLE-NS"
    aps-published-ts: "1715153983"
    aps-ssl: "data-api.tls"
    aps-data-plane: "data-plane-1"
    aps-template-version: "v2"

spec:
  host: abc.api.gov.bc.ca
  port:
    targetPort: kong-proxy
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
    certificate: |-
      <-- SSL GOES HERE -->
    key: |-
      <-- SSL GOES HERE -->
  to:
    kind: Service
    name: data-plane-1
    weight: 100
  wildcardPolicy: None
status:
  ingress:
  - host: abc.api.gov.bc.ca
    routerName: router
    wildcardPolicy: None 

---
"""

def mock_apply_routes (rootPath):
    print(rootPath)
    with open("%s/routes-current.yaml" % rootPath) as f:
        assert route_new_yaml == f.read()


def test_bulk_sync_new_route(client):

    with mock.patch('clients.ocp_routes.time_secs') as dt:
        dt.return_value = 1715153983

        with mock.patch("routers.routes.get_gwa_ocp_routes") as call:
            call.return_value = []

            with mock.patch("clients.ocp_routes.read_and_indent") as call_ssl:
                call_ssl.return_value = "      <-- SSL GOES HERE -->"

                with mock.patch("clients.ocp_routes.prepare_route_last_version") as call_last_ver:
                    call_last_ver.return_value = []

                    with mock.patch("routers.routes.apply_routes") as call_mismatch_routes:
                        call_mismatch_routes.side_effect = mock_apply_routes

                        data = [{
                            "name": "wild-ns-example",
                            "selectTag": "ns.EXAMPLE-NS",
                            "dataPlane": "data-plane-1",
                            "host": "abc.api.gov.bc.ca",
                            "sessionCookieEnabled": False,
                            "dataClass": None,
                            "sslCertificateSerialNumber": None,
                            "certificates": []
                        }]
                        response = client.post('/namespaces/examplens/routes/sync', json=data)
                        assert response.status_code == 200
                        assert response.json()['message'] == 'synced'
                        assert response.json()['inserted_count'] == 1
                        
route_new_custom_yaml = f"""
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: wild-ns-EXAMPLE-NS-abc.custom.gov.bc.ca
  resourceVersion: ""
  annotations:
    haproxy.router.openshift.io/balance: random
    haproxy.router.openshift.io/disable_cookies: 'true'
    haproxy.router.openshift.io/timeout: 30m

  labels:
    aps-generated-by: "gwa-cli"
    aps-published-on: "2024.05-May.08"
    aps-namespace: "examplens"
    aps-select-tag: "ns.EXAMPLE-NS"
    aps-published-ts: "1715153983"
    aps-ssl: "custom"
    aps-data-plane: "data-plane-1"
    aps-template-version: "v2"
    aps-certificate-serial: "1"
spec:
  host: abc.custom.gov.bc.ca
  port:
    targetPort: kong-proxy
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
    certificate: |-
        {SAMPLE_CERT_FORMATTED}
    key: |-
        {SAMPLE_KEY_FORMATTED}
  to:
    kind: Service
    name: data-plane-1
    weight: 100
  wildcardPolicy: None
status:
  ingress:
  - host: abc.custom.gov.bc.ca
    routerName: router
    wildcardPolicy: None 

---
"""

def mock_apply_routes_custom (rootPath):
    print(rootPath)
    with open("%s/routes-current.yaml" % rootPath) as f:
        assert route_new_custom_yaml == f.read()


def test_bulk_sync_new_route_custom(client):

    with mock.patch('clients.ocp_routes.time_secs') as dt:
        dt.return_value = 1715153983

        with mock.patch("routers.routes.get_gwa_ocp_routes") as call:
            call.return_value = []

            with mock.patch("clients.ocp_routes.prepare_route_last_version") as call_last_ver:
                call_last_ver.return_value = []

                with mock.patch("routers.routes.apply_routes") as call_mismatch_routes:
                    call_mismatch_routes.side_effect = mock_apply_routes_custom

                    data = [{
                        "name": "wild-ns-example",
                        "selectTag": "ns.EXAMPLE-NS",
                        "dataPlane": "data-plane-1",
                        "host": "abc.custom.gov.bc.ca",
                        "sessionCookieEnabled": False,
                        "dataClass": None,
                        "sslCertificateSerialNumber": "1",
                        "certificates": [                
                            {
                                "id": "41d14845-669f-4dcd-aff2-926fb32a4b25",
                                "snis": [ "abc.custom.gov.bc.ca" ],
                                "cert": SAMPLE_CERT,
                                "created_at": 1731713874,
                                "tags": [
                                    "ns.ns1"
                                ],
                                "key": SAMPLE_KEY,
                            }              
                        ]
                    }]
                    response = client.post('/namespaces/examplens/routes/sync', json=data)
                    assert response.status_code == 200
                    assert response.json()['message'] == 'synced'
                    assert response.json()['inserted_count'] == 1


