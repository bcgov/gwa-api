from unittest import mock

def test_local_tls(client):
    with mock.patch("routers.routes.get_gwa_ocp_service_secrets") as get:
        get.return_value = [
            {
                "host": "abc.api.gov.bc.ca",
                'data': {
                    'data': {
                        'tls.crt': "",
                        'tls.key': ""
                    }
                }    
            }
        ]
        response = client.get('/namespaces/EXAMPLE-NS/local_tls')
        assert response.status_code == 200
        assert response.json()[0]['tags'][0] == 'gwa.ns.EXAMPLE-NS'
        assert response.json()[0]['snis'][0] == 'abc.api.gov.bc.ca'
