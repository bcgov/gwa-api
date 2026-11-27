import json
from copy import deepcopy
from pathlib import Path

import pytest

from utils.masking import mask, mask_plugin, scrub_text

CASES_PATH = Path(__file__).resolve().parents[2] / "utils" / "masking" / "cases.json"
with CASES_PATH.open(encoding="utf-8") as cases_file:
    SHARED_CASES = json.load(cases_file)["cases"]

CERT_DIFF = """\
updating certificate 8fc131ef-9752-43a4-ba70-eb10ba442d4e
-  "key": "-----BEGIN PRIVATE KEY-----\\nOLDPRIVATEKEYDATA\\n-----END PRIVATE KEY-----",
+  "key": "-----BEGIN PRIVATE KEY-----\\nNEWPRIVATEKEYDATA\\n-----END PRIVATE KEY-----",
-  "key_alt": "-----BEGIN RSA PRIVATE KEY-----\\nOLDALTKEYDATA\\n-----END RSA PRIVATE KEY-----",
+  "key_alt": "-----BEGIN OPENSSH PRIVATE KEY-----\\nNEWALTKEYDATA\\n-----END OPENSSH PRIVATE KEY-----",
   "cert": "-----BEGIN CERTIFICATE-----\\nMIIBCERTBODY\\n-----END CERTIFICATE-----"
"""


def _case_id(case):
    return "%s: %s" % (case["kind"], case["name"])


@pytest.mark.parametrize("case", SHARED_CASES, ids=_case_id)
def test_shared_masking_case(case):
    if case["kind"] == "plugin":
        actual = mask_plugin(deepcopy(case["input"]))
    elif case["kind"] == "text":
        actual = scrub_text(case["input"])
    else:
        raise AssertionError("unknown case kind %s" % case["kind"])
    assert actual == case["expected"]


def test_mask_certificate_update_diff():
    masked = mask(CERT_DIFF)
    assert "BEGIN PRIVATE KEY" not in masked
    assert "BEGIN RSA PRIVATE KEY" not in masked
    assert "BEGIN OPENSSH PRIVATE KEY" not in masked
    assert "OLDPRIVATEKEYDATA" not in masked
    assert "NEWPRIVATEKEYDATA" not in masked
    assert "OLDALTKEYDATA" not in masked
    assert "NEWALTKEYDATA" not in masked
    assert "-----BEGIN CERTIFICATE-----\\nMIIBCERTBODY\\n-----END CERTIFICATE-----" in masked


def test_mask_nested_plugin_secret():
    diff = """\
-      "client_secret": "s9",
+      "password": "nested-secret",
       "client_id": "my-client"
"""
    masked = mask(diff)
    assert "s9" not in masked
    assert "nested-secret" not in masked
    assert '"client_secret": "****"' in masked
    assert '"password": "****"' in masked
    assert '"client_id": "my-client"' in masked


def test_mask_auth_header_line():
    diff = """\
+        "Authorization:Bearer abc123def",
         "X-Request-Source:portal"
"""
    masked = mask(diff)
    assert "abc123def" not in masked
    assert "Authorization:Bearer ****" in masked
    assert "X-Request-Source:portal" in masked


def test_mask_replaces_platform_redis_literals():
    from utils.masking import conf

    redis = conf["plugins"]["rate_limiting"]
    host = redis["redis_host"]
    password = redis["redis_password"]
    masked = mask("redis %s %s end" % (host, password))
    assert host not in masked
    assert password not in masked
    assert masked == "redis **** **** end"


def test_mask_skips_empty_redis_literals(monkeypatch):
    from utils import masking

    rate = masking.conf["plugins"]["rate_limiting"]
    monkeypatch.setitem(rate, "redis_password", "")
    monkeypatch.setitem(rate, "redis_host", "")
    assert masking.mask("a b") == "a b"
