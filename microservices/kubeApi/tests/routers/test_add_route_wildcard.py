from unittest import mock

def mock_apply_routes_empty(rootPath):
    print(rootPath)
    with open("%s/routes-current.yaml" % rootPath) as f:
        assert f.read() == "---\n"

def mock_apply_routes(rootPath):
    print(rootPath)
    with open("%s/routes-current.yaml" % rootPath) as f:
        content = f.read()
        assert routes_current_yaml == content

def test_skip_route(client):
    """Test that routes ending in .api.gov.bc.ca are skipped when wildcard_enabled is True and conditions match"""
    with mock.patch('routers.routes.wildcard_enabled', {'enabled': True}):
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

                                with mock.patch("routers.routes.apply_routes") as call_apply_routes:
                                    call_apply_routes.side_effect = mock_apply_routes_empty

                                    with mock.patch("routers.routes.prepare_apply_routes") as call_prepare_apply:
                                        call_prepare_apply.return_value = 0

                                        data = {
                                            "hosts": ["abc.api.gov.bc.ca"],
                                            "select_tag": "ns.EXAMPLE-NS",
                                            "ns_attributes": {
                                                "perm-data-plane": ["data-plane-1"],
                                            },
                                            "overrides": {
                                                "aps.route.session.cookie.enabled": [],
                                                "aps.route.dataclass.low": [],
                                                "aps.route.dataclass.medium": ["abc.api.gov.bc.ca"],
                                                "aps.route.dataclass.high": [],
                                                "aps.route.dataclass.public": []
                                            }
                                        }
                                        response = client.put('/namespaces/examplens/routes', json=data)
                                        assert response.status_code == 201
                                        # Verify that prepare_apply_routes was called with empty hosts list
                                        call_prepare_apply.assert_called_once()
                                        hosts_arg = call_prepare_apply.call_args[0][2]
                                        assert hosts_arg == []

def test_create_route(client):
    """Test that routes ending in .api.gov.bc.ca are created when wildcard_enabled is False"""
    with mock.patch('routers.routes.wildcard_enabled', {'enabled': False}):
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

                                with mock.patch("routers.routes.apply_routes") as call_apply_routes:
                                    call_apply_routes.side_effect = mock_apply_routes

                                    with mock.patch("routers.routes.prepare_apply_routes") as call_prepare_apply:
                                        call_prepare_apply.return_value = 0

                                        data = {
                                            "hosts": ["abc.api.gov.bc.ca"],
                                            "select_tag": "ns.EXAMPLE-NS",
                                            "ns_attributes": {
                                                "perm-data-plane": ["data-plane-1"],
                                            },
                                            "overrides": {
                                                "aps.route.session.cookie.enabled": [],
                                                "aps.route.dataclass.low": [],
                                                "aps.route.dataclass.medium": ["abc.api.gov.bc.ca"],
                                                "aps.route.dataclass.high": [],
                                                "aps.route.dataclass.public": []
                                            }
                                        }
                                        response = client.put('/namespaces/examplens/routes', json=data)
                                        assert response.status_code == 201
                                        assert response.json()['message'] == 'created'
                                        # Verify that prepare_apply_routes was called with non-empty hosts list
                                        call_prepare_apply.assert_called_once()
                                        hosts_arg = call_prepare_apply.call_args[0][2]
                                        assert len(hosts_arg) > 0
                                        assert "abc.api.gov.bc.ca" in hosts_arg

def test_skip_route_host_matches_r1_pattern(client):
    """Test that routes matching R1 patterns are skipped when wildcard_enabled is True"""
    with mock.patch('routers.routes.wildcard_enabled', {'enabled': True}):
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

                                with mock.patch("routers.routes.apply_routes") as call_apply_routes:
                                    call_apply_routes.side_effect = mock_apply_routes_empty

                                    with mock.patch("routers.routes.prepare_apply_routes") as call_prepare_apply:
                                        call_prepare_apply.return_value = 0

                                        # Test with .dev.api.gov.bc.ca pattern
                                        data = {
                                            "hosts": ["test.dev.api.gov.bc.ca"],
                                            "select_tag": "ns.EXAMPLE-NS",
                                            "ns_attributes": {
                                                "perm-data-plane": ["data-plane-1"],
                                            },
                                            "overrides": {
                                                "aps.route.session.cookie.enabled": [],
                                                "aps.route.dataclass.low": [],
                                                "aps.route.dataclass.medium": ["test.dev.api.gov.bc.ca"],
                                                "aps.route.dataclass.high": [],
                                                "aps.route.dataclass.public": []
                                            }
                                        }
                                        response = client.put('/namespaces/examplens/routes', json=data)
                                        assert response.status_code == 201
                                        call_prepare_apply.assert_called_once()
                                        hosts_arg = call_prepare_apply.call_args[0][2]
                                        assert hosts_arg == []

def test_create_route_cookies_enabled(client):
    """Test that routes are created when session_cookie_enabled is True even if other conditions match"""
    with mock.patch('routers.routes.wildcard_enabled', {'enabled': True}):
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

                                with mock.patch("routers.routes.apply_routes") as call_apply_routes:
                                    call_apply_routes.side_effect = mock_apply_routes

                                    with mock.patch("routers.routes.prepare_apply_routes") as call_prepare_apply:
                                        call_prepare_apply.return_value = 0

                                        # Test with cookies enabled - should NOT be skipped
                                        data = {
                                            "hosts": ["abc.api.gov.bc.ca"],
                                            "select_tag": "ns.EXAMPLE-NS",
                                            "ns_attributes": {
                                                "perm-data-plane": ["data-plane-1"],
                                            },
                                            "overrides": {
                                                "aps.route.session.cookie.enabled": ["abc.api.gov.bc.ca"],
                                                "aps.route.dataclass.low": [],
                                                "aps.route.dataclass.medium": ["abc.api.gov.bc.ca"],
                                                "aps.route.dataclass.high": [],
                                                "aps.route.dataclass.public": []
                                            }
                                        }
                                        response = client.put('/namespaces/examplens/routes', json=data)
                                        assert response.status_code == 201
                                        call_prepare_apply.assert_called_once()
                                        hosts_arg = call_prepare_apply.call_args[0][2]
                                        assert len(hosts_arg) > 0
                                        assert "abc.api.gov.bc.ca" in hosts_arg

def test_create_route_dataclass_not_medium(client):
    """Test that routes are created when dataclass is not 'medium' even if other conditions match"""
    with mock.patch('routers.routes.wildcard_enabled', {'enabled': True}):
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

                                with mock.patch("routers.routes.apply_routes") as call_apply_routes:
                                    call_apply_routes.side_effect = mock_apply_routes

                                    with mock.patch("routers.routes.prepare_apply_routes") as call_prepare_apply:
                                        call_prepare_apply.return_value = 0

                                        # Test with dataclass high - should NOT be skipped
                                        data = {
                                            "hosts": ["abc.api.gov.bc.ca"],
                                            "select_tag": "ns.EXAMPLE-NS",
                                            "ns_attributes": {
                                                "perm-data-plane": ["data-plane-1"],
                                            },
                                            "overrides": {
                                                "aps.route.session.cookie.enabled": [],
                                                "aps.route.dataclass.low": [],
                                                "aps.route.dataclass.medium": [],
                                                "aps.route.dataclass.high": ["abc.api.gov.bc.ca"],
                                                "aps.route.dataclass.public": []
                                            }
                                        }
                                        response = client.put('/namespaces/examplens/routes', json=data)
                                        assert response.status_code == 201
                                        call_prepare_apply.assert_called_once()
                                        hosts_arg = call_prepare_apply.call_args[0][2]
                                        assert len(hosts_arg) > 0
                                        assert "abc.api.gov.bc.ca" in hosts_arg

def test_create_route_non_r1_host(client):
    """Test that routes are created for non-R1 hosts even if other conditions match"""
    with mock.patch('routers.routes.wildcard_enabled', {'enabled': True}):
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

                                with mock.patch("routers.routes.apply_routes") as call_apply_routes:
                                    call_apply_routes.side_effect = mock_apply_routes

                                    with mock.patch("routers.routes.prepare_apply_routes") as call_prepare_apply:
                                        call_prepare_apply.return_value = 0

                                        # Test with non-R1 host - should NOT be skipped
                                        data = {
                                            "hosts": ["custom.example.com"],
                                            "select_tag": "ns.EXAMPLE-NS",
                                            "ns_attributes": {
                                                "perm-data-plane": ["data-plane-1"],
                                            },
                                            "overrides": {
                                                "aps.route.session.cookie.enabled": [],
                                                "aps.route.dataclass.low": [],
                                                "aps.route.dataclass.medium": ["custom.example.com"],
                                                "aps.route.dataclass.high": [],
                                                "aps.route.dataclass.public": []
                                            }
                                        }
                                        response = client.put('/namespaces/examplens/routes', json=data)
                                        assert response.status_code == 201
                                        call_prepare_apply.assert_called_once()
                                        hosts_arg = call_prepare_apply.call_args[0][2]
                                        assert len(hosts_arg) > 0
                                        assert "custom.example.com" in hosts_arg

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
