from clients.uma.resourceset import map_res_name_to_id

def test_map_res_name_to_id(mocker, app):
    # Mock the Flask app 'config' and 'logger'
    class mock_patch:
        config = {
            "resourceAuthServer": {
                "serverUrl": "http://keycloak",
                "realm": "master"
            }
        }
        logger = app.logger
    mocker.patch('clients.uma.resourceset.app', mock_patch)

    # Mock the response from Keycloak to get a particular resourceset
    class mock_resourceset:
        status_code = 200
        def json():
            return [
                "ecbae046-e0bc-4e96-a3f5-22efb50fef34"
            ]
    mocker.patch("clients.uma.resourceset.requests.get", return_value=mock_resourceset)

    id = map_res_name_to_id(None, "NS_RESOURCE")
    assert id == "ecbae046-e0bc-4e96-a3f5-22efb50fef34"
