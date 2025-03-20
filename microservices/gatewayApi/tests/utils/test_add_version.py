

from utils.transforms import add_version_if_missing
import yaml

def test_add_version_with_format():
    payload = '''
_format_version: 3.0
services:
- host: myservice
  name: my-service
  tags:
  - ns.mytest
  - another
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)

    add_version_if_missing(y)

    result =  yaml.dump(y, indent=2)

    assert payload.strip() == result.strip()

def test_add_version_if_missing():
    payload = '''
services:
- host: myservice
  name: my-service
  tags:
  - ns.mytest
  - another
'''

    expected = '''
_format_version: 3.0
services:
- host: myservice
  name: my-service
  tags:
  - ns.mytest
  - another
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)

    add_version_if_missing(y)

    result =  yaml.dump(y, indent=2)

    assert expected.strip() == result.strip()


def test_add_version_with_v1():
    payload = '''
_format_version: 1.0
services:
- host: myservice
  name: my-service
  tags:
  - ns.mytest
  - another
'''

    expected = '''
_format_version: 3.0
services:
- host: myservice
  name: my-service
  tags:
  - ns.mytest
  - another
'''
    y = yaml.load(payload, Loader=yaml.FullLoader)

    add_version_if_missing(y)

    result =  yaml.dump(y, indent=2)

    assert expected.strip() == result.strip()