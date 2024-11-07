from unittest import mock

def test_bulk_sync_no_change(client):
    with mock.patch("routers.routes.get_gwa_ocp_routes") as call:
        call.return_value = [{
            "metadata": {
                "name": "wild-ns-example",
                "labels": {
                    "aps-select-tag": "ns.EXAMPLE-NS",
                    "aps-template-version": "v1"
                },
                "annotations": {
                }
            },
            "spec": {
                "host": "abc.api.gov.bc.ca",
                "to": {
                    "name": "data-plane-1"
                }
            }
        }]

        with mock.patch("routers.routes.prepare_apply_routes") as call_apply:
            call_apply.return_value = 0

            with mock.patch("routers.routes.apply_routes") as call_matched_routes:
                call_matched_routes.return_value = None

                data = [{
                    "name": "wild-ns-example",
                    "selectTag": "ns.EXAMPLE-NS",
                    "dataPlane": "data-plane-1",
                    "host": "abc.api.gov.bc.ca",
                    "sessionCookieEnabled": True,
                    "dataClass": None
                }]
                response = client.post('/namespaces/examplens/routes/sync', json=data)
                assert response.status_code == 200
                assert response.json()['message'] == 'synced'

routes_session_cookie_yaml = """
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: wild-ns-EXAMPLE-NS-abc.api.gov.bc.ca
  resourceVersion: ""
  annotations:
    haproxy.router.openshift.io/timeout: 30m

  labels:
    aps-generated-by: "gwa-cli"
    aps-published-on: "2024.05-May.08"
    aps-namespace: "examplens"
    aps-select-tag: "ns.EXAMPLE-NS"
    aps-published-ts: "1715153983"
    aps-ssl: "data-api.tls"
    aps-data-plane: "data-plane-1"
    aps-template-version: "v1"
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

def mock_apply_routes_session_cookie (rootPath):
    print(rootPath)
    with open("%s/routes-current.yaml" % rootPath) as f:
        assert routes_session_cookie_yaml == f.read()

def test_bulk_sync_new_route_session_cookie(client):

    with mock.patch('clients.ocp_routes.time_secs') as dt:
        dt.return_value = 1715153983

        with mock.patch("routers.routes.get_gwa_ocp_routes") as call:
            call.return_value = []

            with mock.patch("clients.ocp_routes.read_and_indent") as call_ssl:
                call_ssl.return_value = "      <-- SSL GOES HERE -->"

                with mock.patch("clients.ocp_routes.prepare_route_last_version") as call_last_ver:
                    call_last_ver.return_value = []

                    with mock.patch("routers.routes.apply_routes") as call_mismatch_routes:
                        call_mismatch_routes.side_effect = mock_apply_routes_session_cookie

                        data = [{
                            "name": "wild-ns-example",
                            "selectTag": "ns.EXAMPLE-NS",
                            "dataPlane": "data-plane-1",
                            "host": "abc.api.gov.bc.ca",
                            "sessionCookieEnabled": True,
                            "dataClass": None
                        }]
                        response = client.post('/namespaces/examplens/routes/sync', json=data)
                        assert response.status_code == 200
                        assert response.json()['message'] == 'synced'
                        assert response.json()['inserted_count'] == 1

def test_bulk_sync_change_session_cookie(client):
    with mock.patch('clients.ocp_routes.time_secs') as dt:
        dt.return_value = 1715153983

        with mock.patch("routers.routes.get_gwa_ocp_routes") as mock_get_routes:
            mock_get_routes.return_value = [{
                    "metadata": {
                        "name": "wild-ns-example",
                        "labels": {
                            "aps-select-tag": "ns.EXAMPLE-NS",
                            "aps-template-version": "v2"
                        },
                        "annotations": {
                        }
                    },
                    "spec": {
                        "host": "abc.api.gov.bc.ca",
                        "to": {
                            "name": "data-plane-1"
                        }
                    }
                }]

            with mock.patch("clients.ocp_routes.read_and_indent") as call_ssl:
                call_ssl.return_value = "      <-- SSL GOES HERE -->"

                with mock.patch("clients.ocp_routes.prepare_route_last_version") as call_last_ver:
                    call_last_ver.return_value = []

                    with mock.patch("routers.routes.apply_routes") as call_mismatch_routes:
                        call_mismatch_routes.side_effect = mock_apply_routes_session_cookie

                        data = [{
                            "name": "wild-ns-example",
                            "selectTag": "ns.EXAMPLE-NS",
                            "dataPlane": "data-plane-1",
                            "host": "abc.api.gov.bc.ca",
                            "sessionCookieEnabled": True,
                            "dataClass": None
                        }]
                        response = client.post('/namespaces/examplens/routes/sync', json=data)
                        assert response.status_code == 200
                        assert response.json()['message'] == 'synced'
                        assert response.json()['inserted_count'] == 1
                        assert response.json()['deleted_count'] == 0

routes_data_class_yaml = """
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: wild-ns-EXAMPLE-NS-abc.api.gov.bc.ca
  resourceVersion: ""
  annotations:
    haproxy.router.openshift.io/balance: random
    haproxy.router.openshift.io/disable_cookies: 'true'
    haproxy.router.openshift.io/timeout: 30m
    aviinfrasetting.ako.vmware.com/name: "dataclass-high"
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

def mock_apply_routes_data_class (rootPath):
    print(rootPath)
    with open("%s/routes-current.yaml" % rootPath) as f:
        assert routes_data_class_yaml == f.read()


def test_bulk_sync_new_route_data_class(client):

    with mock.patch('clients.ocp_routes.time_secs') as dt:
        dt.return_value = 1715153983

        with mock.patch("routers.routes.get_gwa_ocp_routes") as call:
            call.return_value = []

            with mock.patch("clients.ocp_routes.read_and_indent") as call_ssl:
                call_ssl.return_value = "      <-- SSL GOES HERE -->"

                with mock.patch("clients.ocp_routes.prepare_route_last_version") as call_last_ver:
                    call_last_ver.return_value = []

                    with mock.patch("routers.routes.apply_routes") as call_mismatch_routes:
                        call_mismatch_routes.side_effect = mock_apply_routes_data_class

                        data = [{
                            "name": "wild-ns-example",
                            "selectTag": "ns.EXAMPLE-NS",
                            "dataPlane": "data-plane-1",
                            "host": "abc.api.gov.bc.ca",
                            "sessionCookieEnabled": False,
                            "dataClass": "high"
                        }]
                        response = client.post('/namespaces/examplens/routes/sync', json=data)
                        assert response.status_code == 200
                        assert response.json()['message'] == 'synced'
                        assert response.json()['inserted_count'] == 1

def test_bulk_sync_add_data_class(client):
    with mock.patch('clients.ocp_routes.time_secs') as dt:
        dt.return_value = 1715153983

        with mock.patch("routers.routes.get_gwa_ocp_routes") as mock_get_routes:
            mock_get_routes.return_value = [{
                    "metadata": {
                        "name": "wild-ns-example",
                        "labels": {
                            "aps-select-tag": "ns.EXAMPLE-NS",
                            "aps-template-version": "v2"
                        },
                        "annotations": {
                        }
                    },
                    "spec": {
                        "host": "abc.api.gov.bc.ca",
                        "to": {
                            "name": "data-plane-1"
                        }
                    }
                }]

            with mock.patch("clients.ocp_routes.read_and_indent") as call_ssl:
                call_ssl.return_value = "      <-- SSL GOES HERE -->"

                with mock.patch("clients.ocp_routes.prepare_route_last_version") as call_last_ver:
                    call_last_ver.return_value = []

                    with mock.patch("routers.routes.apply_routes") as call_mismatch_routes:
                        call_mismatch_routes.side_effect = mock_apply_routes_data_class

                        data = [{
                            "name": "wild-ns-example",
                            "selectTag": "ns.EXAMPLE-NS",
                            "dataPlane": "data-plane-1",
                            "host": "abc.api.gov.bc.ca",
                            "sessionCookieEnabled": False,
                            "dataClass": "high"
                        }]
                        response = client.post('/namespaces/examplens/routes/sync', json=data)
                        assert response.status_code == 200
                        assert response.json()['message'] == 'synced'
                        assert response.json()['inserted_count'] == 1
                        assert response.json()['deleted_count'] == 0

def test_bulk_sync_remove_data_class(client):
    with mock.patch('clients.ocp_routes.time_secs') as dt:
        dt.return_value = 1715153983

        with mock.patch("routers.routes.get_gwa_ocp_routes") as mock_get_routes:
            mock_get_routes.return_value = [{
                    "metadata": {
                        "name": "wild-ns-example",
                        "labels": {
                            "aps-select-tag": "ns.EXAMPLE-NS",
                            "aps-template-version": "v1"
                        },
                        "annotations": {
                            "aviinfrasetting.ako.vmware.com/name": "dataclass-medium"
                        }
                    },
                    "spec": {
                        "host": "abc.api.gov.bc.ca",
                        "to": {
                            "name": "data-plane-1"
                        }
                    }
                }]

            with mock.patch("clients.ocp_routes.read_and_indent") as call_ssl:
                call_ssl.return_value = "      <-- SSL GOES HERE -->"

                with mock.patch("clients.ocp_routes.prepare_route_last_version") as call_last_ver:
                    call_last_ver.return_value = []

                    with mock.patch("routers.routes.apply_routes") as call_mismatch_routes:
                        call_mismatch_routes.side_effect = mock_apply_routes_session_cookie

                        data = [{
                            "name": "wild-ns-example",
                            "selectTag": "ns.EXAMPLE-NS",
                            "dataPlane": "data-plane-1",
                            "host": "abc.api.gov.bc.ca",
                            "sessionCookieEnabled": True,
                            "dataClass": None
                        }]
                        response = client.post('/namespaces/examplens/routes/sync', json=data)
                        assert response.status_code == 200
                        assert response.json()['message'] == 'synced'
                        assert response.json()['inserted_count'] == 1
                        assert response.json()['deleted_count'] == 0

def test_bulk_sync_change_data_class(client):
    with mock.patch('clients.ocp_routes.time_secs') as dt:
        dt.return_value = 1715153983

        with mock.patch("routers.routes.get_gwa_ocp_routes") as mock_get_routes:
            mock_get_routes.return_value = [{
                    "metadata": {
                        "name": "wild-ns-example",
                        "labels": {
                            "aps-select-tag": "ns.EXAMPLE-NS",
                            "aps-template-version": "v2"
                        },
                        "annotations": {
                            "aviinfrasetting.ako.vmware.com/name": "dataclass-medium"
                        }
                    },
                    "spec": {
                        "host": "abc.api.gov.bc.ca",
                        "to": {
                            "name": "data-plane-1"
                        }
                    }
                }]

            with mock.patch("clients.ocp_routes.read_and_indent") as call_ssl:
                call_ssl.return_value = "      <-- SSL GOES HERE -->"

                with mock.patch("clients.ocp_routes.prepare_route_last_version") as call_last_ver:
                    call_last_ver.return_value = []

                    with mock.patch("routers.routes.apply_routes") as call_mismatch_routes:
                        call_mismatch_routes.side_effect = mock_apply_routes_data_class

                        data = [{
                            "name": "wild-ns-example",
                            "selectTag": "ns.EXAMPLE-NS",
                            "dataPlane": "data-plane-1",
                            "host": "abc.api.gov.bc.ca",
                            "sessionCookieEnabled": False,
                            "dataClass": "high"
                        }]
                        response = client.post('/namespaces/examplens/routes/sync', json=data)
                        assert response.status_code == 200
                        assert response.json()['message'] == 'synced'
                        assert response.json()['inserted_count'] == 1
                        assert response.json()['deleted_count'] == 0