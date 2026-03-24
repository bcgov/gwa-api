# SDX CA Token API

A FastAPI microservice that wraps the `step ca token` CLI to generate one-time-use tokens for the Step CA certificate authority.

See [sdx-ca-token-api-spec.md](sdx-ca-token-api-spec.md) for the full specification.

## Endpoints

| Method | Path      | Description                          |
|--------|-----------|--------------------------------------|
| POST   | `/token`  | Generate a one-time CA token         |
| GET    | `/health` | Health / readiness check             |

## Environment Variables

| Variable                       | Required | Default                            | Description                       |
|--------------------------------|----------|------------------------------------|-----------------------------------|
| `STEP_CA_URL`                  | Yes      |                                    | In-cluster CA URL                 |
| `STEP_CA_FINGERPRINT`          | Yes      |                                    | Root CA fingerprint for bootstrap |
| `LOG_LEVEL`                    | No       | `DEBUG`                            | Python log level                  |
| `STEP_PROVISIONER_PASSWORD_FILE` | No     | `/etc/step-provisioner/password`   | Path to provisioner password file |
| `STEP_PROVISIONER_KID`         | No       |                                    | Provisioner key ID                |
| `STEP_PROVISIONER_ISSUER`      | No       |                                    | Provisioner issuer name           |

## Local Development

```bash
# Install dependencies
cd microservices/sdxStepTokenApi
poetry install

# Run the app (requires step CLI and CA access)
export STEP_CA_URL='https://your-ca-host:443'
export STEP_CA_FINGERPRINT='your-sha256-fingerprint-hex'
export STEP_PROVISIONER_PASSWORD_FILE="$HOME/sdx-provisioner-password"
# optional:
# export STEP_PROVISIONER_KID='...'
# export STEP_PROVISIONER_ISSUER='...'
poetry run uvicorn main:app --host 0.0.0.0 --port 8080

# Run tests
poetry run pytest -s

# Run tests with coverage
poetry run coverage run --branch -m pytest -s
poetry run coverage xml
```

## Docker

```bash
docker build -t sdx-ca-token-api .

docker run --rm -ti \
  -p 8080:8080 \
  -e STEP_CA_URL='https://your-ca-host:443' \
  -e STEP_CA_FINGERPRINT='your-sha256-fingerprint-hex' \
  -e STEP_PROVISIONER_PASSWORD_FILE=/etc/step-provisioner/password \
  -v /absolute/path/on/your/machine/provisioner-password:/etc/step-provisioner/password:ro \
  sdx-ca-token-api
```
