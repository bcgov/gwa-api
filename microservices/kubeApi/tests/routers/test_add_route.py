
from unittest import mock

routes_current_yaml = """
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
        assert routes_current_yaml == f.read()

def test_add_route_override(client):
    with mock.patch('clients.ocp_routes.time_secs') as dt:
        dt.return_value = 1715153983

        with mock.patch("routers.routes.prepare_apply_services") as call:
            call.return_value = 0

            with mock.patch("routers.routes.prepare_mismatched_services") as call_mismatch:
                call_mismatch.return_value = 0

                with mock.patch("clients.ocp_routes.read_and_indent") as call_ssl:
                    call_ssl.return_value = "      <-- SSL GOES HERE -->"

                    with mock.patch("clients.ocp_routes.prepare_route_last_version") as call_last_ver:
                        call_last_ver.return_value = []

                        with mock.patch("routers.routes.prepare_mismatched_routes") as call_mismatch_routes:
                            call_mismatch_routes.return_value = 0

                            with mock.patch("routers.routes.apply_routes") as call_mismatch_routes:
                                call_mismatch_routes.side_effect = mock_apply_routes

                                data = {
                                    "hosts": [ "abc.api.gov.bc.ca" ],
                                    "select_tag": "ns.EXAMPLE-NS",
                                    "ns_attributes": {
                                        "perm-data-plane": ["data-plane-1"]
                                    }
                                }
                                response = client.put('/namespaces/examplens/routes', json=data)
                                assert response.status_code == 201
                                assert response.json()['message'] == 'created'
