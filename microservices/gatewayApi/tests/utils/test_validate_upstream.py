

# def test_index(client):
#     response = client.get('/')
#     assert response.data == b'["http://localhost/v1/status"]\n'

import yaml
import pytest
from utils.validators import validate_upstream

def test_upstream_good(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    host: myservice
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    validate_upstream (y, { }, [])

def test_upstream_localhost(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    host: localhost
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    with pytest.raises(Exception, match=r"service upstream is invalid \(e1\)"):
        validate_upstream (y, { }, [])

def test_upstream_127(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    host: 127.0.0.1
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    with pytest.raises(Exception, match=r"service upstream is invalid \(e1\)"):
        validate_upstream (y, { "perm-project": ["ns.mytest"]}, [])

def test_upstream_url(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    url: http://localhost:4000
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    with pytest.raises(Exception, match=r"service upstream is invalid \(e1\)"):
        validate_upstream (y, { "perm-project": ["ns.mytest"]}, [])

def test_upstream_invalid_url(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    url: localhost:4000
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    with pytest.raises(Exception, match=r"service upstream has invalid url specified \(e1\)"):
        validate_upstream (y, { "perm-project": ["ns.mytest"]}, [])


def test_upstream_valid_service(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    host: myapi.my-namespace.svc
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    validate_upstream (y, { "perm-project": ["ns.mytest"]}, [])

def test_upstream_protected_service_allow(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    host: myapi.my-namespace.svc
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    validate_upstream (y, { "perm-protected-ns": ["allow"]}, ['my-namespace'])

def test_upstream_protected_service(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    host: myapi.my-namespace.svc
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    with pytest.raises(Exception, match=r"service upstream is invalid \(e3\)"):
        validate_upstream (y, {}, ['my-namespace'])

def test_upstream_protected_service_deny(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    host: myapi.my-namespace.svc
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    with pytest.raises(Exception, match=r"service upstream is invalid \(e3\)"):
        validate_upstream (y, { "perm-protected-ns": ["deny"]}, ['my-namespace'])

def test_upstream_invalid_host(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    host: my-namespace.svc
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    with pytest.raises(Exception, match=r"service upstream is invalid \(e2\)"):
        validate_upstream (y, { "perm-protected-ns": ["deny"]}, ['my-namespace'])

def test_upstream_protected_service_allow(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    host: myapi.my-other-namespace.svc
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)
    validate_upstream (y, { "perm-protected-ns": ["deny"]}, ['my-namespace']) 

def test_upstream_pass_validation(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    host: myapi.my-namespace.svc
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)

    validate_upstream (y, { "perm-upstreams": ["my-namespace"]}, [], True) 

def test_upstream_pass_validation_exact_match(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    host: 192.168.1.1
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)

    validate_upstream (y, { "perm-upstreams": ["192.168.1.1"]}, [], True) 

def test_upstream_fail_validation(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    host: myapi.my-namespace.svc
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)

    with pytest.raises(Exception, match=r"service upstream is invalid \(e6\)"):
        validate_upstream (y, {}, [], True)

    with pytest.raises(Exception, match=r"service upstream is invalid \(e6\)"):
        validate_upstream (y, { "perm-upstreams": ["other-namespace"]}, [], True)

    with pytest.raises(Exception, match=r"service upstream is invalid \(e6\)"):
        validate_upstream (y, { "perm-upstreams": [""]}, [], True)
