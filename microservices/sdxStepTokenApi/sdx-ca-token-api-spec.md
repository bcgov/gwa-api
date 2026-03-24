# SDX Step CA Token API — Microservice Spec

## Purpose

A FastAPI microservice that wraps the `step ca token` CLI to generate one-time-use tokens for the Step CA certificate authority. Callers use these tokens to obtain X.509 certificates from the CA.

This service runs in the same OpenShift namespace as the Step CA server and is accessed only by other services in the namespace (no external route).

---

## API Specification

### `POST /token`

Generate a one-time token for the Step CA.

#### Request Body

```json
{
  "subject": "my-service.clients.sdx",
  "san": ["alt-name-1.clients.sdx", "10.0.0.5"]
}
```

| Field     | Type           | Required | Description                                                                                                                                                                                                                                                                 |
| --------- | -------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `subject` | `string`       | Yes      | The Common Name / DNS Name / IP for the certificate. Must match one of the CA template rules above. When there are no additional Subject Alternative Names configured (via the --san flag), the subject will be added as the only element of the 'sans' claim on the token. |
| `san`     | `list[string]` | No       | Additional Subject Alternative Names (DNS, IP, email, URI).                                                                                                                                                                                                                 |

#### Response `200 OK`

```json
{
  "token": "<one-time-use JWT token>"
}
```

#### Response `500 Internal Server Error`

```json
{
  "detail": "Failed to generate token: <stderr from step CLI>"
}
```

### `GET /health`

Basic health/readiness check.

#### Response `200 OK`

```json
{
  "status": "ok"
}
```

---

## Implementation Details

### CLI Command Construction

The service shells out to the `step` CLI. Example invocation:

```bash
step ca token my-service.clients.sdx \
  --provisioner-password-file /etc/step-provisioner/password \
  --san alt-name-1.clients.sdx \
  --san 10.0.0.5
```

- `--provisioner-password-file` is mounted as a Kubernetes secret.
- `--san` is repeated for each entry in the optional `san` list.
- All other flags use CA defaults (provisioner selection via `--kid`/`--issuer` may be needed depending on the provisioner config in tfvars — check at implementation time).
- `--ca-url` and `--root` are omitted; they come from environment / bootstrap (see below).

### Startup: Bootstrap Root Certificate

On startup (before serving requests), the application must bootstrap the root CA cert:

```bash
step ca bootstrap \
  --ca-url $STEP_CA_URL \
  --fingerprint $STEP_CA_FINGERPRINT
```

This writes the root cert to `~/.step/certs/root_ca.crt` (the default `STEPPATH`). After bootstrap, subsequent `step ca token` commands can omit `--root` entirely since it becomes the default.

Run this as part of application startup (e.g., a FastAPI lifespan event). If bootstrap fails, the service should not become ready.

### Environment Variables

| Variable              | Description                       | Example                                               |
| --------------------- | --------------------------------- | ----------------------------------------------------- |
| `STEP_CA_URL`         | In-cluster CA URL                 | `https://sdx-ca-step-certificates.b8840c-dev.svc:443` |
| `STEP_CA_FINGERPRINT` | Root CA fingerprint for bootstrap | `abc123...` (SHA-256 hex)                             |
| `LOG_LEVEL`           | Python log level                  | `DEBUG`                                               |

### Mounted Secrets

| Mount Path                       | Source Secret     | Description                                                            |
| -------------------------------- | ----------------- | ---------------------------------------------------------------------- |
| `/etc/step-provisioner/password` | (TBD secret name) | Provisioner password file, referenced by `--provisioner-password-file` |

### Logging

Log the following on each token request:

- `subject`
- `san` (if provided)
- Success/failure status
- Timestamp

Use structured JSON logging to match other services in the platform.

---

## Access / Auth

- **Internal only**: No OpenShift Route. The service is accessed via its in-cluster Kubernetes Service DNS name (e.g., `sdx-ca-token-api-generic-api.<namespace>.svc`).
- **No authentication layer** required — network isolation within the namespace provides access control.

---

## Summary Checklist

- FastAPI app with `POST /token` and `GET /health`
- Pydantic model: `subject` (required str), `san` (optional list of str)
- `step ca bootstrap` at startup (lifespan event), fail if unsuccessful
- Shell out to `step ca token` with constructed args
- Structured JSON logging of subject/SAN on each request
- Dockerfile with Python + step CLI
- Unit tests (mock subprocess calls)
- No external route — internal cluster access only
