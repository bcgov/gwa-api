from clients.ocp_routes import eval_services

def test_eval_services_route_tags():

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

def test_eval_services_service_tags():
    
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
            },
            {
                "routes": [
                    {
                        "hosts": [
                            "host2"
                        ],
                        "tags": []
                    },
                    {
                        "hosts": [
                            "host3"
                        ],
                        "tags": []
                    }
                ],
                "tags": [
                    "tag2",
                    "override-tag"
                ]
            }
        ]
    }
    host_list = []
    eval_services(host_list, 'override-tag', data)
    assert len(host_list) == 3
    assert host_list[0] == 'host1'
    assert host_list[1] == 'host2'
    assert host_list[2] == 'host3'