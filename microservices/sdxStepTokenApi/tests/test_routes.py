from unittest.mock import patch
from fastapi.testclient import TestClient

# Patch bootstrap before importing app so the lifespan doesn't try to call
# the real step CLI during tests.
with patch('clients.step.bootstrap'):
    from app import create_app

    app = create_app()
    client = TestClient(app)


@patch('routers.routes.generate_token')
def test_create_token_success(mock_generate):
    mock_generate.return_value = "eyJhbGciOiJFUzI1NiJ9.payload.sig"

    response = client.post("/token", json={
        "subject": "my-service.clients.sdx",
        "san": ["alt.clients.sdx", "10.0.0.5"],
    })

    assert response.status_code == 200
    data = response.json()
    assert data["token"] == "eyJhbGciOiJFUzI1NiJ9.payload.sig"
    mock_generate.assert_called_once_with(
        subject="my-service.clients.sdx",
        san=["alt.clients.sdx", "10.0.0.5"],
        provisioner_password_file="/etc/step-provisioner/password",
        provisioner_kid="",
        provisioner_issuer="",
    )


@patch('routers.routes.generate_token')
def test_create_token_no_san(mock_generate):
    mock_generate.return_value = "token-no-san"

    response = client.post("/token", json={
        "subject": "my-service.clients.sdx",
    })

    assert response.status_code == 200
    data = response.json()
    assert data["token"] == "token-no-san"
    mock_generate.assert_called_once_with(
        subject="my-service.clients.sdx",
        san=None,
        provisioner_password_file="/etc/step-provisioner/password",
        provisioner_kid="",
        provisioner_issuer="",
    )


@patch('routers.routes.generate_token')
def test_create_token_failure(mock_generate):
    mock_generate.side_effect = RuntimeError(
        "Failed to generate token: error from step CLI"
    )

    response = client.post("/token", json={
        "subject": "my-service.clients.sdx",
    })

    assert response.status_code == 500
    data = response.json()
    assert "Failed to generate token" in data["detail"]


def test_create_token_missing_subject():
    response = client.post("/token", json={})

    assert response.status_code == 422


def test_create_token_missing_subject_with_san():
    response = client.post("/token", json={
        "san": ["alt.clients.sdx"],
    })

    assert response.status_code == 422


def test_create_token_invalid_body():
    response = client.post("/token", content="not json",
                           headers={"Content-Type": "application/json"})

    assert response.status_code == 422


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
