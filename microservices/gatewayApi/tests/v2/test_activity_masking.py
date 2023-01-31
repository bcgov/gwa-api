import yaml
import pytest
from clients.ocp_gateway_secret import prep_submitted_config

def test_activity_masking(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    host: myservice
    plugins:
    - name: my-plguin
      config:
        secret: s3r3t
        another: true
'''
    yaml_documents_iter = yaml.load_all(payload, Loader=yaml.FullLoader)

    yaml_documents = []
    for doc in yaml_documents_iter:
        yaml_documents.append(doc)

    result = prep_submitted_config(yaml_documents, True)
    assert ("secret: '*****'" in result)

def test_activity_masking_route_test(app):
    payload = '''
services:
  - name: my-service
    tags: ["ns.mytest", "another"]
    host: myservice
    routes:
    - name: route-1
      plugins:
        - name: my-plugin
          config:
            secret2: s3cr3t
            password: s3cr3t
            username: s3cr3t
            private_key_location: /tmp/ssl/cert.key
            client_secret: "1234-1232-32123-12321"
            another: true
'''
    yaml_documents_iter = yaml.load_all(payload, Loader=yaml.FullLoader)

    yaml_documents = []
    for doc in yaml_documents_iter:
        yaml_documents.append(doc)

    result = prep_submitted_config(yaml_documents, True)
    print (result)
    assert ("username: '*****'" in result)
    assert ("password: '*****'" in result)
    assert ("client_secret: '*****'" in result)
    assert ("private_key_location: '*****'" in result)
    assert ("secret2: s3cr3t" in result)

def test_activity_masking_certs_test(app):
    payload = '''
certificates:
  - key: "-----BEGIN OPENSSH PRIVATE KEY-----\n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\n-----END OPENSSH PRIVATE KEY-----\n"
    cert: "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDaZ9y43uYxvr3FR1PxUy2VdAAcCSQaGtOleb61YMxxx+/adtfWXkbEdKbArp3NpKbvXj4MRtmPIkzQuZFDb6kCcetwEql6hqwAbji5bDfhU/SbqUff6JPLiZYezrE1lVtPsdpJ4poe5DpQYjCQP0T4dz2S6MwYeaqixqqKVcd5hDMZf1YYwOh3ecoLY3vR08Cvyeu2S5US0fimYM3IsROlSyDcMqRqGINljUjNGYIVc+VdOESGprFBOvpDSNMxJECS4h+Vw238+vsAIu+UWhAkmaqPXQibbNQ5zXa/ZR6ZSODxJjT60vOKxt8+A7HLvP2C0wpGuVs/yDJN8UX56GD8n38q74R1+vefOEvsFOGB09tmQpYe+z/3TMty8Zj4bdH1jCgrqIjZQ/fnqpNE6EhAGr4L4IGjBs/pqeKjOg5TEOsrkk879Sq3xLZlapzVVCs3EaCembPDoEXFXHZJpwibgpX8IkIURjfT0NJvl7UltzA3L3bXbid9UahvahK64mE=\n"
'''
    yaml_documents_iter = yaml.load_all(payload, Loader=yaml.FullLoader)

    yaml_documents = []
    for doc in yaml_documents_iter:
        yaml_documents.append(doc)

    result = prep_submitted_config(yaml_documents, True)
    print (result)
    assert ("key: '*****'" in result)
    assert ("cert: ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDaZ9y43uYxvr...JpwibgpX8IkIURjfT0NJvl7UltzA3L3bXbid9UahvahK64mE=" in result)
