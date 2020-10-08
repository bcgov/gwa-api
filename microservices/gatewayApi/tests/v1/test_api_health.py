

# def test_index(client):
#     response = client.get('/')
#     assert response.data == b'["http://localhost/v1/status"]\n'

import yaml
import pytest
from v1.routes.gateway import validate_tags

def test_validate_tags_good_scenario():
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    routes:
    - name: route-1
      tags: ["ns.mytest", "another2"]
      plugins.
      - name: acl-auth
        tags: ["ns.mytest"]
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    validate_tags (y, "ns.mytest")

def test_validate_tags_illegal_tag():
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest-bad", "another"]
    routes:
    - name: route-1
      tags: ["ns.mytest", "another2"]
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    with pytest.raises(Exception, match=r"^.services.my-service missing required tag ns.mytest,.services.my-service invalid ns tag ns.mytest-bad"):
        result = validate_tags (y, "ns.mytest")

def test_validate_tags_missing_required_tag():
    payload = '''
services:
  - name: my-service
    tags: ["another"]
    routes:
    - name: route-1
      tags: ["ns.mytest", "another2"]
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    with pytest.raises(Exception, match=r"^.services.my-service missing required tag ns.mytest"):
        result = validate_tags (y, "ns.mytest")

def test_validate_tags_missing_required_route_tag():
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another2"]
    routes:
    - name: route-1
      tags: ["another2"]
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    with pytest.raises(Exception, match=r"^.services.my-service.routes.route-1 missing required tag ns.mytest"):
        result = validate_tags (y, "ns.mytest")

def test_validate_tags_missing_plugin_tag():
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    routes:
    - name: route-1
      tags: ["ns.mytest", "another2"]
      plugins.
      - name: acl-auth
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    with pytest.raises(Exception, match=r"^.services.my-service.routes.route-1.plugins.acl-auth no tags found"):
        result = validate_tags (y, "ns.mytest")
