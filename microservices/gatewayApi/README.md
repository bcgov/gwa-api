# GWA Kong API

## Getting Started

Install requires access to the Kong Admin API.

### Prerequisites

- Python 3.6 or newer
- Docker 18.09.1 or newer

### Bare Metal Install

Create a default.json file from default.json.example under the config directory and edit the values to ones for your environment.  
Consider using `virtualenv` to isolate this Python environment from other Python programs.  
Run `pip install -r requirements.txt` to install dependencies and `python3 wsgi.py` to start up the server.

- _Windows Note: Other endpoints may not be able to resolve localhost and/or 127.0.0.1. You may change `wsgi.py` to listen from `0.0.0.0` to compensate, but DO NOT commit this to git!_

### Docker Install

Run `docker build . -t gwa_kong_api` to build the docker container and the following commands to run it

```sh
hostip=$(ifconfig en0 | awk '$1 == "inet" {print $2}')

docker run -ti --rm \
 -e CONFIG_PATH=/tmp/production.json -e ENVIRONMENT=production \
 -e OIDC_BASE_URL=https://auth.cloud/auth/realms/aps \
 -e TOKEN_MATCH_AUD=account \
 -e WORKING_FOLDER=/tmp \
 -e KONG_ADMIN_URL=https://adminapi.cloud  \
 -e KC_SERVER_URL=https://auth.cloud/auth/ \
 -e KC_REALM=aps \
 -e KC_USERNAME=kcadmin \
 -e KC_PASSWORD="" \
 -e KC_USER_REALM=master \
 -e KC_CLIENT_ID=admin-cli \
 -e HOST_TRANSFORM_ENABLED=true \
 -e HOST_TRANSFORM_BASE_URL=api.cloud \
 -e PLUGINS_RATELIMITING_REDIS_PASSWORD="" \
 -e DATA_PLANES_CONFIG_PATH=/dp/data_planes_config.json \
 -v `pwd`/_tmp:/ssl \
 -v `pwd`/_tmp:/dp/ \
 -v ~/.kube/config:/root/.kube/config \
 --add-host=docker:$hostip -p 2000:2000 gwa_kong_api
```

The `data_planes_config.json` example:

```
{
  "data_planes": {
    "dp-silver-kong-proxy": {
      "kube-api": "https://api.cloud",
      "kube-ns": "xxxxxx-dev"
    }
  }
}
```

- _Windows Note: the `--add-host=docker:$hostip` parameter and hostip line are not necessary._

Replace the configuration values as necessary and LOCALPORT with the local port you want to have the service on.

Go to: http://localhost:2000/docs/

### Helm Install

```sh
helm upgrade --install gwa-kong-api --namespace ocwa bcgov/generic-api
```

### Development

Locally running:

```sh
uvicorn wsgi:app --host 0.0.0.0 --port 8080 --reload
```

Testing:

```sh
ENV=test GITHASH=11223344 \
poetry run coverage run --branch -m pytest -s
coverage xml
```
