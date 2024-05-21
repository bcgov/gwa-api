from unittest import mock

def test_del_route(client):
    with mock.patch("routers.routes.kubectl_delete") as call_delete:
        call_delete.return_value = None

        response = client.delete('/namespaces/EXAMPLE-NS/routes/ROUTE-NAME')
        assert response.status_code == 204
