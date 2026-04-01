import yaml
import pytest
from utils.validators import validate_route_paths


ALLOWED_PREFIX = "/sdx/0/LAB.MIN.CITZ.DATA-USAGE.v1"
SECOND_ALLOWED_PREFIX = "/sdx/0/LAB.MIN.CITZ.OTHER-USAGE.v1"


def test_route_paths_validation_disabled(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    routes:
      - name: my-route
        paths:
          - /not-allowed
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    validate_route_paths(y, {}, False)


def test_route_paths_good_single_match(app):
    payload = f'''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    routes:
      - name: my-route
        paths:
          - {ALLOWED_PREFIX}/users
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    validate_route_paths(y, {"perm-route-paths": [ALLOWED_PREFIX]}, True)


def test_route_paths_good_exact_match(app):
    payload = f'''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    routes:
      - name: my-route
        paths:
          - {ALLOWED_PREFIX}
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    validate_route_paths(y, {"perm-route-paths": [ALLOWED_PREFIX]}, True)


def test_route_paths_good_multiple_allowed_prefixes(app):
    payload = f'''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    routes:
      - name: my-route
        paths:
          - {SECOND_ALLOWED_PREFIX}/orders
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    validate_route_paths(
        y,
        {"perm-route-paths": [ALLOWED_PREFIX, SECOND_ALLOWED_PREFIX]},
        True,
    )


def test_route_paths_good_multiple_paths_all_valid(app):
    payload = f'''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    routes:
      - name: my-route
        paths:
          - {ALLOWED_PREFIX}/users
          - {ALLOWED_PREFIX}/orders
          - {ALLOWED_PREFIX}/status
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    validate_route_paths(y, {"perm-route-paths": [ALLOWED_PREFIX]}, True)


def test_route_paths_good_path_without_leading_slash(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    routes:
      - name: my-route
        paths:
          - sdx/0/LAB.MIN.CITZ.DATA-USAGE.v1/users
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    validate_route_paths(y, {"perm-route-paths": [ALLOWED_PREFIX]}, True)


def test_route_paths_fail_no_perm_route_paths(app):
    payload = f'''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    routes:
      - name: my-route
        paths:
          - {ALLOWED_PREFIX}/users
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)

    with pytest.raises(Exception, match=r"service\.my-service\.route\.my-route.*does not match any allowed paths \(e7\)"):
        validate_route_paths(y, {}, True)


def test_route_paths_fail_empty_perm_route_paths(app):
    payload = f'''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    routes:
      - name: my-route
        paths:
          - {ALLOWED_PREFIX}/users
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)

    with pytest.raises(Exception, match=r"service\.my-service\.route\.my-route.*does not match any allowed paths \(e7\)"):
        validate_route_paths(y, {"perm-route-paths": [""]}, True)


def test_route_paths_fail_not_matching_allowed_prefix(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    routes:
      - name: my-route
        paths:
          - /sdx/0/LAB.MIN.CITZ.UNRELATED.v1/users
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)

    with pytest.raises(Exception, match=r"service\.my-service\.route\.my-route.*does not match any allowed paths \(e7\)"):
        validate_route_paths(
            y,
            {"perm-route-paths": [ALLOWED_PREFIX, SECOND_ALLOWED_PREFIX]},
            True,
        )


def test_route_paths_fail_one_of_multiple_paths_invalid(app):
    payload = f'''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    routes:
      - name: my-route
        paths:
          - {ALLOWED_PREFIX}/users
          - /sdx/0/LAB.MIN.CITZ.UNRELATED.v1/users
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)

    with pytest.raises(Exception, match=r"service\.my-service\.route\.my-route.*does not match any allowed paths \(e7\)"):
        validate_route_paths(y, {"perm-route-paths": [ALLOWED_PREFIX]}, True)


def test_route_paths_fail_multiple_routes_one_invalid(app):
    payload = f'''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    routes:
      - name: route-1
        paths:
          - {ALLOWED_PREFIX}/users
      - name: route-2
        paths:
          - /sdx/0/LAB.MIN.CITZ.UNRELATED.v1/health
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)

    with pytest.raises(Exception, match=r"service\.my-service\.route\.route-2.*does not match any allowed paths \(e7\)"):
        validate_route_paths(y, {"perm-route-paths": [ALLOWED_PREFIX]}, True)


def test_route_paths_good_multiple_routes_all_valid(app):
    payload = f'''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    routes:
      - name: route-1
        paths:
          - {ALLOWED_PREFIX}/users
      - name: route-2
        paths:
          - {ALLOWED_PREFIX}/orders
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    validate_route_paths(y, {"perm-route-paths": [ALLOWED_PREFIX]}, True)


def test_route_paths_multiple_services_one_invalid(app):
    payload = f'''
services:
  - name: service-1
    tags: ["ns.mytest", "another"]
    routes:
      - name: route-1
        paths:
          - {ALLOWED_PREFIX}/users
  - name: service-2
    tags: ["ns.mytest", "another"]
    routes:
      - name: route-2
        paths:
          - /sdx/0/LAB.MIN.CITZ.UNRELATED.v1/users
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)

    with pytest.raises(Exception, match=r"service\.service-2\.route\.route-2.*does not match any allowed paths \(e7\)"):
        validate_route_paths(y, {"perm-route-paths": [ALLOWED_PREFIX]}, True)


def test_route_paths_fail_similar_prefix_not_matching(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    routes:
      - name: my-route
        paths:
          - /sdx/0/LAB.MIN.CITZ.DATA-USAGE.v10/users
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)

    with pytest.raises(Exception, match=r"service\.my-service\.route\.my-route.*does not match any allowed paths \(e7\)"):
        validate_route_paths(y, {"perm-route-paths": [ALLOWED_PREFIX]}, True)