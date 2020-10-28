# GWA Kong API

## Installation

Install requires access to the Kong Admin API.

### Prerequisites

- Python 3.6 or newer
- Docker 18.09.1 or newer

### Bare Metal Install

Create a default.json file from default.json.example under the config directory and edit the values to ones for your environment.  
Consider using `virtualenv` to isolate this Python environment from other Python programs.  
Run `pip install -r requirements.txt` to install dependencies and `python3 wsgi.py` to start up the server.

- *Windows Note: Other endpoints may not be able to resolve localhost and/or 127.0.0.1. You may change `wsgi.py` to listen from `0.0.0.0` to compensate, but DO NOT commit this to git!*

### Docker Install

Run `docker build . -t gwa_kong_api` to build the docker container and the following commands to run it

``` sh
hostip=$(ifconfig en0 | awk '$1 == "inet" {print $2}')

docker run -ti --rm \
 -e CONFIG_PATH=/tmp/production.json -e ENVIRONMENT=production \
 -e OIDC_BASE_URL=https://auth-qwzrwc-dev.pathfinder.gov.bc.ca/auth/realms/aps \
 -e TOKEN_MATCH_AUD=account \
 -e WORKING_FOLDER=/tmp \
 -e KONG_ADMIN_URL=https://adminapi-qwzrwc-dev.pathfinder.gov.bc.ca  \
 -e KC_SERVER_URL=https://auth-qwzrwc-dev.pathfinder.gov.bc.ca/auth/ \
 -e KC_REALM=aps \
 -e KC_USERNAME=kcadmin \
 -e KC_PASSWORD="SdufuSYnFAANnluWrAH0waHavE9YWdCu" \
 -e KC_USER_REALM=master \
 -e KC_CLIENT_ID=admin-cli \
 -v `pwd`/_tmp:/ssl \
 -v ~/.kube/config:/root/.kube/config \
 --add-host=docker:$hostip -p 2000:2000 gwa_kong_api
```

- *Windows Note: the `--add-host=docker:$hostip` parameter and hostip line are not necessary.*

Replace the configuration values as necessary and LOCALPORT with the local port you want to have the service on.

## Helm



### Helm Install (Kubernetes)

``` sh
helm upgrade --install gwa-kong-api --namespace ocwa bcgov/generic-api
```


## Test

``` sh
pip install '.[test]'
ENVIRONMENT=test pytest --verbose
```

Run with coverage support. The report will be generated in htmlcov/index.html.

``` sh
coverage run -m pytest
coverage report
coverage html
```
