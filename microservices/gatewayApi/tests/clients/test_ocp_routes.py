from clients.ocp_routes import eval_services

def test_eval_services():

    data = {
        "services": [
            {},
            {
                "routes": [
                ]
            },
            {
                "routes": [
                    {
                        "hosts": [],
                        "tags": []
                    }
                ]
            },
            {
                "routes": [
                    {
                        "hosts": [
                            "host1"
                        ],
                        "tags": [
                            "tag1",
                            "override-tag"
                        ]
                    }
                ]
            }
        ]
    }
    host_list = []
    eval_services(host_list, 'override-tag', data)
    assert len(host_list) == 1
    assert host_list[0] == 'host1'