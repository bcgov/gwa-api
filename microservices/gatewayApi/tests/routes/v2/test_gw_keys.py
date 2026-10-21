import json
from clients.kong import strip_private_key_material


PRIVATE_JWK = {
    "kty": "EC",
    "crv": "P-256",
    "x": "public-x",
    "y": "public-y",
    "d": "super-secret-d",
}


def _key_payload(include_private=True):
    jwk = dict(PRIVATE_JWK)
    if not include_private:
        jwk.pop("d")
    return {
        "id": "key-1",
        "name": "sdx.keys.rg.dev.edge:abc",
        "kid": "urn:ca:bc:sdx:edge:rg:dev:abc",
        "set": {"id": "set-1", "name": "sdx.edge.rg.dev"},
        "tags": ["ns.mytest.key-rg-dev"],
        "pem": {
            "public_key": "-----BEGIN PUBLIC KEY-----",
            "private_key": "-----BEGIN PRIVATE KEY-----SECRET",
        },
        "jwk": json.dumps(jwk),
    }


def test_strip_private_key_material_removes_pem_and_jwk_secrets():
    original = _key_payload()
    cleaned = strip_private_key_material(original)
    assert "private_key" not in cleaned["pem"]
    parsed = json.loads(cleaned["jwk"])
    assert "d" not in parsed
    assert parsed["x"] == "public-x"
    # original is not mutated
    assert "private_key" in original["pem"]
    assert "d" in json.loads(original["jwk"])


def test_strip_private_key_material_omits_unparseable_jwk():
    original = _key_payload()
    original["jwk"] = "not-json{"
    cleaned = strip_private_key_material(original)
    assert "jwk" not in cleaned
    assert original["jwk"] == "not-json{"


def test_strip_private_key_material_omits_non_object_jwk():
    original = _key_payload()
    original["jwk"] = json.dumps(["not", "an", "object"])
    cleaned = strip_private_key_material(original)
    assert "jwk" not in cleaned


def test_strip_private_key_material_omits_unexpected_pem():
    original = _key_payload()
    original["pem"] = "-----BEGIN PRIVATE KEY-----SECRET"
    cleaned = strip_private_key_material(original)
    assert "pem" not in cleaned
    assert original["pem"] == "-----BEGIN PRIVATE KEY-----SECRET"


def test_get_keys_empty(client, mocker):
    mocker.patch(
        "v2.routes.gw_keys.get_keys_and_key_sets",
        return_value={"key_sets": [], "keys": []},
    )
    response = client.get("/v2/namespaces/mytest/keys")
    assert response.status_code == 200
    assert response.json == {"key_sets": [], "keys": []}


def test_get_keys_single_and_multi(client, mocker):
    payload = {
        "key_sets": [{"id": "set-1", "name": "sdx.edge.rg.dev"}],
        "keys": [
            strip_private_key_material(_key_payload()),
            strip_private_key_material(
                {
                    **_key_payload(),
                    "id": "key-2",
                    "kid": "urn:ca:bc:sdx:edge:rg:dev:def",
                    "name": "sdx.keys.rg.dev.edge:def",
                }
            ),
        ],
    }
    mocker.patch("v2.routes.gw_keys.get_keys_and_key_sets", return_value=payload)

    response = client.get(
        "/v2/namespaces/mytest/keys?tag=ns.mytest.key-rg-dev&key_set=sdx.edge.rg.dev"
    )
    assert response.status_code == 200
    body = response.json
    assert len(body["keys"]) == 2
    assert all("private_key" not in (k.get("pem") or {}) for k in body["keys"])
    assert all("d" not in json.loads(k["jwk"]) for k in body["keys"])


def test_get_keys_invalid_tag(client):
    response = client.get("/v2/namespaces/mytest/keys?tag=ns.other.qualifier")
    assert response.status_code == 400


def test_get_keys_unauthorized(client, mocker):
    mocker.patch("auth.uma.enforce", return_value=False)
    response = client.get("/v2/namespaces/mytest/keys")
    assert response.status_code == 403


def test_get_keys_and_key_sets_filters_and_strips(mocker):
    keys = [
        {
            "id": "k1",
            "set": {"id": "set-1"},
            "pem": {"private_key": "secret", "public_key": "pub"},
        },
        {
            "id": "k2",
            "set": {"id": "set-2"},
            "pem": {"public_key": "pub2"},
        },
    ]
    key_sets = [
        {"id": "set-1", "name": "sdx.edge.rg.dev"},
        {"id": "set-2", "name": "other"},
    ]

    def fake_recurse(result, url, base_url=None):
        if url.startswith("/keys"):
            result.extend(keys)
        else:
            result.extend(key_sets)
        return result

    mocker.patch("clients.kong.recurse_get_records", side_effect=fake_recurse)
    from clients.kong import get_keys_and_key_sets

    out = get_keys_and_key_sets("ns.mytest.key-rg-dev", "sdx.edge.rg.dev")
    assert [ks["name"] for ks in out["key_sets"]] == ["sdx.edge.rg.dev"]
    assert [k["id"] for k in out["keys"]] == ["k1"]
    assert "private_key" not in out["keys"][0]["pem"]
