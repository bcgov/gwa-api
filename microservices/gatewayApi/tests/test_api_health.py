from os import environ

def test_version(client):
    response = client.get('/version')
    assert response.status_code == 200
    assert response.json['hash'] == environ.get('GITHASH')
