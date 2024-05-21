from unittest import mock
import pytest
import json
import traceback
from fastapi import HTTPException

from clients.ocp_routes import apply_routes, delete_routes, \
    kubectl_apply, kubectl_delete, \
    prepare_mismatched_routes, prepare_route_last_version, prepare_apply_routes, \
    get_gwa_ocp_routes

class mock_popen_instance:
    # class decoded_response:
    #     def __init__ (self, output):
    #         self.output = output
    #     def decode(self, utf):
    #         return self.output

    def __init__ (self, output, returncode):
        self.output = output
        self.returncode = returncode
    def communicate(self):
        return self.output, None


def test_happy_kubectl_apply():
    
    with mock.patch("clients.ocp_routes.Popen") as popen:
        popen.return_value = mock_popen_instance('some data', 0)

        kubectl_apply('/testfile')

def test_error_kubectl_apply():
    
    with mock.patch("clients.ocp_routes.Popen") as popen:
        popen.return_value = mock_popen_instance('failed to do something', 127)

        with pytest.raises(HTTPException) as excinfo:
            kubectl_apply('/testfile')

        assert excinfo.value.detail == 'Failed to apply routes'

def test_happy_kubectl_delete():
    
    with mock.patch("clients.ocp_routes.Popen") as popen:
        popen.return_value = mock_popen_instance('some data', 0)

        kubectl_delete('type', 'name')

def test_happy_apply_routes():
    
    with mock.patch("clients.ocp_routes.Popen") as popen:
        popen.return_value = mock_popen_instance('some data', 0)

        apply_routes('/testfile')

def test_happy_delete_routes():
    
    with mock.patch("clients.ocp_routes.Popen") as popen:
        popen.return_value = mock_popen_instance('some data', 0)

        delete_routes('/testfile')

def test_prepare_mismatched_routes():
    existing_routes = {
        "items": [
            {
                "metadata": {
                    "name": "wild-asp-route-1"
                }
            }
        ]
    }
    with mock.patch("clients.ocp_routes.Popen") as popen:
        popen.return_value = mock_popen_instance(json.dumps(existing_routes), 0)

        prepare_mismatched_routes('ns.NS', ['host1'], '/tmp')

def test_prepare_route_last_version():
    existing_routes = {
        "items": [
            {
                "metadata": {
                    "name": "wild-asp-route-1",
                    "resourceVersion": "1"
                }
            }
        ]
    }
    with mock.patch("clients.ocp_routes.Popen") as popen:
        popen.return_value = mock_popen_instance(json.dumps(existing_routes), 0)

        res_versions = prepare_route_last_version(None, 'ns.NS')
        assert json.dumps(res_versions) == '{"wild-asp-route-1": "1"}'


def test_prepare_apply_routes():
    existing_routes = {
        "items": [
            {
                "metadata": {
                    "name": "wild-asp-route-1",
                    "resourceVersion": "1"
                }
            }
        ]
    }
    with mock.patch('clients.ocp_routes.read_and_indent') as read:
        read.return_value = "SSLCERT"
        with mock.patch("clients.ocp_routes.Popen") as popen:
            popen.return_value = mock_popen_instance(json.dumps(existing_routes), 0)

            ns = "NS1"
            select_tag = "ns.NS1"
            hosts = [ "host1", "host2" ]
            root_path = "/tmp"
            data_plane = "test-dp"
            ns_template_version = "v2"
            overrides = None
            host_count = prepare_apply_routes(ns, select_tag, hosts, root_path, data_plane, ns_template_version, overrides)
            assert host_count == 2
                     
def test_get_gwa_ocp_routes():
    existing_routes = {
        "items": [
            {
                "metadata": {
                    "name": "wild-asp-route-1",
                    "resourceVersion": "1"
                }
            }
        ]
    }
    with mock.patch("clients.ocp_routes.Popen") as popen:
        popen.return_value = mock_popen_instance(json.dumps(existing_routes), 0)

        routes = get_gwa_ocp_routes()
        assert json.dumps(routes) == json.dumps(existing_routes['items'])

def test_failed_get_gwa_ocp_routes():
    existing_routes = {
        "items": [
            {
                "metadata": {
                    "name": "wild-asp-route-1"
                }
            }
        ]
    }
    with mock.patch("clients.ocp_routes.Popen") as popen:
        popen.return_value = mock_popen_instance(json.dumps(existing_routes), -1)

        with pytest.raises(Exception) as excinfo:
            get_gwa_ocp_routes()
    
        assert excinfo.value.args[0] == 'Failed to get existing routes'
