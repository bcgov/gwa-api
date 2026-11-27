import yaml
from clients.ocp_gateway_secret import prep_submitted_config

CERT_BODY = (
    "-----BEGIN CERTIFICATE-----\n"
    + ("ABCDEFGHIJ" * 12)
    + "\n-----END CERTIFICATE-----\n"
)
PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----\nSECRETKEYMATERIAL\n-----END PRIVATE KEY-----\n"
OPENSSH_KEY = "-----BEGIN OPENSSH PRIVATE KEY-----\nALTSECRET\n-----END OPENSSH PRIVATE KEY-----\n"


def _masked(document):
    rendered = prep_submitted_config([document], True)
    loaded = list(yaml.load_all(rendered, Loader=yaml.FullLoader))
    return rendered, loaded[0]


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
    document = list(yaml.load_all(payload, Loader=yaml.FullLoader))[0]
    rendered, masked = _masked(document)
    config = masked["services"][0]["plugins"][0]["config"]
    assert config["secret"] == "****"
    assert config["another"] is True
    assert "s3r3t" not in rendered


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
            public_key_location: /tmp/ssl/cert.pub
            client_secret: "1234-1232-32123-12321"
            another: true
'''
    document = list(yaml.load_all(payload, Loader=yaml.FullLoader))[0]
    rendered, masked = _masked(document)
    config = masked["services"][0]["routes"][0]["plugins"][0]["config"]
    assert config["secret2"] == "****"
    assert config["password"] == "****"
    assert config["username"] == "****"
    assert config["client_secret"] == "****"
    assert config["private_key_location"] == "/tmp/ssl/cert.key"
    assert config["public_key_location"] == "/tmp/ssl/cert.pub"
    assert config["another"] is True
    assert "s3cr3t" not in rendered
    assert "1234-1232-32123-12321" not in rendered


def test_activity_masking_certs_test(app):
    document = {
        "certificates": [
            {
                "key": PRIVATE_KEY,
                "key_alt": OPENSSH_KEY,
                "cert": CERT_BODY,
            }
        ],
        "services": [
            {
                "name": "my-service",
                "ca_certificates": ["0000-0000-0000-0000"],
            }
        ],
    }
    rendered, masked = _masked(document)
    certificate = masked["certificates"][0]
    assert certificate["key"] == "****"
    assert certificate["key_alt"] == "****"
    assert certificate["cert"] == CERT_BODY
    assert masked["services"][0]["ca_certificates"] == ["0000-0000-0000-0000"]
    assert "SECRETKEYMATERIAL" not in rendered
    assert "ALTSECRET" not in rendered
    assert "BEGIN PRIVATE KEY" not in rendered
    assert "BEGIN CERTIFICATE" in rendered


def test_activity_masking_nested_redis_and_headers(app):
    document = {
        "services": [
            {
                "name": "my-service",
                "plugins": [
                    {
                        "name": "rate-limiting",
                        "config": {
                            "redis": {
                                "password": "supersecret",
                                "username": "redis-user",
                                "host": "redis.internal",
                            },
                            "second": 5,
                        },
                    },
                    {
                        "name": "request-transformer",
                        "config": {
                            "add": {
                                "headers": [
                                    "Authorization: Bearer secret-token",
                                    "X-API-Key: abc123",
                                    "X-Request-Source: portal",
                                ]
                            },
                            "remove": {"headers": ["Authorization"]},
                            "rename": {"headers": ["Authorization:X-Auth"]},
                        },
                    },
                ],
            }
        ]
    }
    rendered, masked = _masked(document)
    plugins = masked["services"][0]["plugins"]
    redis = plugins[0]["config"]["redis"]
    assert redis["password"] == "****"
    assert redis["username"] == "****"
    assert redis["host"] == "****"
    assert plugins[0]["config"]["second"] == 5
    headers = plugins[1]["config"]
    assert headers["add"]["headers"] == [
        "Authorization:****",
        "X-API-Key:****",
        "X-Request-Source: portal",
    ]
    assert headers["remove"]["headers"] == ["Authorization"]
    assert headers["rename"]["headers"] == ["Authorization:X-Auth"]
    assert "supersecret" not in rendered
    assert "secret-token" not in rendered
    assert "abc123" not in rendered
