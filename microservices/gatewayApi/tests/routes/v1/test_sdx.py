import json


def put_gateway(client, config_file: str, dry_run: bool = False):
    data = {
        "configFile": config_file,
        "dryRun": dry_run,
    }
    return client.put('/v1/namespaces/sdx01/gateway', json=data)


def assert_route_path_error(
    response,
    service_name: str,
    route_name: str,
    path: str,
):
    body = response.get_data(as_text=True)

    assert response.status_code == 400
    assert "does not match any allowed paths (e7)" in body
    assert f"service.{service_name}.route.{route_name}" in body
    assert path in body


def test_success_sdx_call_empty(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.sdx01"]
    '''

    response = put_gateway(client, configFile, False)

    assert response.status_code == 200


def test_success_sdx_call(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.sdx01.qualifier"]
          routes:
          - name: route-1
            hosts: [ sdx01.servers.sdx ]
            tags: ["ns.sdx01.qualifier"]
            plugins:
            - name: acl-auth
              tags: ["ns.sdx01.qualifier"]
    '''

    response = put_gateway(client, configFile, False)

    assert response.status_code == 200


def test_sdx_route_path_validation_pass_v1_exact_match(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.sdx01.qualifier"]
          routes:
          - name: my-route
            hosts: [ sdx01.servers.sdx ]
            paths:
              - /sdx/0/LAB.MIN.CITZ.DATA-USAGE.v1
            tags: ["ns.sdx01.qualifier"]
            plugins:
            - name: acl-auth
              tags: ["ns.sdx01.qualifier"]
    '''

    response = put_gateway(client, configFile, False)

    assert response.status_code == 200


def test_sdx_route_path_validation_pass_v1_child_path(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.sdx01.qualifier"]
          routes:
          - name: my-route
            hosts: [ sdx01.servers.sdx ]
            paths:
              - /sdx/0/LAB.MIN.CITZ.DATA-USAGE.v1/users
            tags: ["ns.sdx01.qualifier"]
            plugins:
            - name: acl-auth
              tags: ["ns.sdx01.qualifier"]
    '''

    response = put_gateway(client, configFile, False)

    assert response.status_code == 200


def test_sdx_route_path_validation_pass_v2_exact_match(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.sdx01.qualifier"]
          routes:
          - name: my-route
            hosts: [ sdx01.servers.sdx ]
            paths:
              - /sdx/0/LAB.MIN.CITZ.DATA-USAGE.v2
            tags: ["ns.sdx01.qualifier"]
            plugins:
            - name: acl-auth
              tags: ["ns.sdx01.qualifier"]
    '''

    response = put_gateway(client, configFile, False)

    assert response.status_code == 200


def test_sdx_route_path_validation_pass_v2_child_path(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.sdx01.qualifier"]
          routes:
          - name: my-route
            hosts: [ sdx01.servers.sdx ]
            paths:
              - /sdx/0/LAB.MIN.CITZ.DATA-USAGE.v2/orders
            tags: ["ns.sdx01.qualifier"]
            plugins:
            - name: acl-auth
              tags: ["ns.sdx01.qualifier"]
    '''

    response = put_gateway(client, configFile, False)

    assert response.status_code == 200


def test_sdx_route_path_validation_fail_invalid_prefix(client):
    invalid_path = "/sdx/0/LAB.MIN.CITZ.INVALID.v1/users"

    configFile = f'''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.sdx01.qualifier"]
          routes:
          - name: my-route
            hosts: [ sdx01.servers.sdx ]
            paths:
              - {invalid_path}
            tags: ["ns.sdx01.qualifier"]
            plugins:
            - name: acl-auth
              tags: ["ns.sdx01.qualifier"]
    '''

    response = put_gateway(client, configFile, False)

    assert_route_path_error(response, "my-service", "my-route", invalid_path)


def test_sdx_route_path_validation_fail_similar_prefix_v10(client):
    invalid_path = "/sdx/0/LAB.MIN.CITZ.DATA-USAGE.v10/users"

    configFile = f'''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.sdx01.qualifier"]
          routes:
          - name: my-route
            hosts: [ sdx01.servers.sdx ]
            paths:
              - {invalid_path}
            tags: ["ns.sdx01.qualifier"]
            plugins:
            - name: acl-auth
              tags: ["ns.sdx01.qualifier"]
    '''

    response = put_gateway(client, configFile, False)

    assert_route_path_error(response, "my-service", "my-route", invalid_path)


def test_sdx_route_path_validation_fail_one_of_multiple_paths_invalid(client):
    valid_path = "/sdx/0/LAB.MIN.CITZ.DATA-USAGE.v1/users"
    invalid_path = "/sdx/0/LAB.MIN.CITZ.INVALID.v1/users"

    configFile = f'''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.sdx01.qualifier"]
          routes:
          - name: my-route
            hosts: [ sdx01.servers.sdx ]
            paths:
              - {valid_path}
              - {invalid_path}
            tags: ["ns.sdx01.qualifier"]
            plugins:
            - name: acl-auth
              tags: ["ns.sdx01.qualifier"]
    '''

    response = put_gateway(client, configFile, False)

    assert_route_path_error(response, "my-service", "my-route", invalid_path)


def test_sdx_route_path_validation_fail_multiple_routes_one_invalid(client):
    invalid_path = "/sdx/0/LAB.MIN.CITZ.INVALID.v1/health"

    configFile = f'''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.sdx01.qualifier"]
          routes:
          - name: route-1
            hosts: [ sdx01.servers.sdx ]
            paths:
              - /sdx/0/LAB.MIN.CITZ.DATA-USAGE.v1/users
            tags: ["ns.sdx01.qualifier"]
          - name: route-2
            hosts: [ sdx01.servers.sdx ]
            paths:
              - {invalid_path}
            tags: ["ns.sdx01.qualifier"]
            plugins:
            - name: acl-auth
              tags: ["ns.sdx01.qualifier"]
    '''

    response = put_gateway(client, configFile, False)

    assert_route_path_error(response, "my-service", "route-2", invalid_path)


def test_sdx_route_path_validation_pass_multiple_routes_all_valid(client):
    configFile = '''
        services:
        - name: my-service
          host: myupstream.local
          tags: ["ns.sdx01.qualifier"]
          routes:
          - name: route-1
            hosts: [ sdx01.servers.sdx ]
            paths:
              - /sdx/0/LAB.MIN.CITZ.DATA-USAGE.v1/users
            tags: ["ns.sdx01.qualifier"]
          - name: route-2
            hosts: [ sdx01.servers.sdx ]
            paths:
              - /sdx/0/LAB.MIN.CITZ.DATA-USAGE.v2/orders
            tags: ["ns.sdx01.qualifier"]
            plugins:
            - name: acl-auth
              tags: ["ns.sdx01.qualifier"]
    '''

    response = put_gateway(client, configFile, False)

    assert response.status_code == 200


def test_sdx_route_path_validation_fail_multiple_services_one_invalid(client):
    invalid_path = "/sdx/0/LAB.MIN.CITZ.INVALID.v1/users"

    configFile = f'''
        services:
        - name: service-1
          host: myupstream.local
          tags: ["ns.sdx01.qualifier"]
          routes:
          - name: route-1
            hosts: [ sdx01.servers.sdx ]
            paths:
              - /sdx/0/LAB.MIN.CITZ.DATA-USAGE.v1/users
            tags: ["ns.sdx01.qualifier"]
        - name: service-2
          host: myupstream.local
          tags: ["ns.sdx01.qualifier"]
          routes:
          - name: route-2
            hosts: [ sdx01.servers.sdx ]
            paths:
              - {invalid_path}
            tags: ["ns.sdx01.qualifier"]
            plugins:
            - name: acl-auth
              tags: ["ns.sdx01.qualifier"]
    '''

    response = put_gateway(client, configFile, False)

    assert_route_path_error(response, "service-2", "route-2", invalid_path)


def test_sdx_route_path_validation_fail_multiple_invalid_paths_reports_all(client):
    invalid_path_1 = "/sdx/0/LAB.MIN.CITZ.INVALID.v1/users"
    invalid_path_2 = "/sdx/0/LAB.MIN.CITZ.DATA-USAGE.v10/orders"

    configFile = f'''
        services:
        - name: service-1
          host: myupstream.local
          tags: ["ns.sdx01.qualifier"]
          routes:
          - name: route-1
            hosts: [ sdx01.servers.sdx ]
            paths:
              - {invalid_path_1}
            tags: ["ns.sdx01.qualifier"]
        - name: service-2
          host: myupstream.local
          tags: ["ns.sdx01.qualifier"]
          routes:
          - name: route-2
            hosts: [ sdx01.servers.sdx ]
            paths:
              - {invalid_path_2}
            tags: ["ns.sdx01.qualifier"]
            plugins:
            - name: acl-auth
              tags: ["ns.sdx01.qualifier"]
    '''

    response = put_gateway(client, configFile, False)
    body = response.get_data(as_text=True)

    assert response.status_code == 400
    assert "does not match any allowed paths (e7)" in body
    assert "service.service-1.route.route-1" in body
    assert invalid_path_1 in body
    assert "service.service-2.route.route-2" in body
    assert invalid_path_2 in body