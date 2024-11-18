from unittest import mock

def test_bulk_sync(client):
    with mock.patch("routers.routes.get_gwa_ocp_routes") as call:
        call.return_value = [{
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


        with mock.patch("routers.routes.prepare_apply_routes") as call_apply:
            call_apply.return_value = 0

            with mock.patch("routers.routes.apply_routes") as call_mismatch_routes:
                call_mismatch_routes.return_value = None

                data = [{
                    "name": "wild-ns-example",
                    "selectTag": "ns.EXAMPLE-NS",
                    "dataPlane": "data-plane-1",
                    "host": "abc.api.gov.bc.ca",
                    "sessionCookieEnabled": False,
                    "dataClass": None,
                    "sslCertificateId": "default",
                    "certificates": None
                }]
                response = client.post('/namespaces/examplens/routes/sync', json=data)
                assert response.status_code == 200
                assert response.json()['message'] == 'synced'
                assert response.json()['inserted_count'] == 0
                assert response.json()['deleted_count'] == 0

def test_bulk_sync_change_host(client):
    with mock.patch("routers.routes.get_gwa_ocp_routes") as call:
        call.return_value = [{
            "metadata": {
                "name": "wild-ns-example-xyz",
                "labels": {
                    "aps-select-tag": "ns.EXAMPLE-NS",
                    "aps-template-version": "v2"
                },
                "annotations": {
                }
            },
            "spec": {
                "host": "xyz.api.gov.bc.ca",
                "to": {
                    "name": "data-plane-1"
                }
            }
        }]


        with mock.patch("routers.routes.prepare_apply_routes") as call_apply:
            call_apply.return_value = 1

            with mock.patch("routers.routes.apply_routes") as call_mismatch_routes:
                call_mismatch_routes.return_value = None

                with mock.patch("routers.routes.delete_route") as mock_delete_route:
                    mock_delete_route.return_value = None  # Simulate successful deletion

                    with mock.patch("routers.routes.kubectl_delete") as mock_kubectl_delete:
                        mock_kubectl_delete.return_value = None  # Simulate successful kubectl deletion

                        data = [{
                            "name": "wild-ns-example-abc",
                            "selectTag": "ns.EXAMPLE-NS",
                            "dataPlane": "data-plane-1",
                            "host": "abc.api.gov.bc.ca",
                            "sessionCookieEnabled": False,
                            "dataClass": None,
                            "sslCertificateId": "default",
                            "certificates": []
                        }]
                        response = client.post('/namespaces/examplens/routes/sync', json=data)
                        assert response.status_code == 200
                        assert response.json()['message'] == 'synced'
                        assert response.json()['inserted_count'] == 1
                        assert response.json()['deleted_count'] == 1

def test_bulk_sync_change_cert(client):
    with mock.patch("routers.routes.get_gwa_ocp_routes") as call:
        call.return_value = [{
            "metadata": {
                "name": "wild-ns-example-abc",
                "labels": {
                    "aps-select-tag": "ns.EXAMPLE-NS",
                    "aps-template-version": "v2",
                    "aps-certificate-id": "41d14845-669f-4dcd-aff2-926fb32a4b25"
                },
                "annotations": {
                }
            },
            "spec": {
                "host": "abc.custom.gov.bc.ca",
                "to": {
                    "name": "data-plane-1"
                }
            }
        }]


        with mock.patch("routers.routes.prepare_apply_routes") as call_apply:
            call_apply.return_value = 1

            with mock.patch("routers.routes.apply_routes") as call_mismatch_routes:
                call_mismatch_routes.return_value = None

                with mock.patch("routers.routes.delete_route") as mock_delete_route:
                    mock_delete_route.return_value = None  # Simulate successful deletion

                    with mock.patch("routers.routes.kubectl_delete") as mock_kubectl_delete:
                        mock_kubectl_delete.return_value = None  # Simulate successful kubectl deletion

                        data = [{
                            "name": "wild-ns-example-abc",
                            "selectTag": "ns.EXAMPLE-NS",
                            "dataPlane": "data-plane-1",
                            "host": "abc.custom.gov.bc.ca",
                            "sessionCookieEnabled": False,
                            "dataClass": None,
                            "sslCertificateId": "default",
                            "certificates": [                
                                {
                                    "id": "afedc6ed-e653-4261-8ec8-17ebaac1fecf",
                                    "snis": [ "abc.custom.gov.bc.ca" ],
                                    "cert": "CERT",
                                    "created_at": 1731713874,
                                    "tags": [
                                        "ns.ns1"
                                    ],
                                    "key": "KEY",
                                }              
                            ] 
                        }]
                        response = client.post('/namespaces/examplens/routes/sync', json=data)
                        assert response.status_code == 200
                        assert response.json()['message'] == 'synced'
                        assert response.json()['inserted_count'] == 1
                        assert response.json()['deleted_count'] == 0

