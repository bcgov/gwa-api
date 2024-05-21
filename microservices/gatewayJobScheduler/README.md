# Kube API

## Getting Started

### Docker

```sh
docker build --tag jobschedulerapi .

docker run -ti --rm --name jobschedulerapi \
  -e SYNC_INTERVAL=1000 \
  -e KONG_ADMIN_API_URL=http://kong \
  -e KUBE_API_URL=http://kubeapi \
  -e KUBE_API_USER=kubeuser \
  -e KUBE_API_PASS=kubepass \
  jobschedulerapi
```

### Development

Locally running:

```sh
SYNC_INTERVAL=1000 \
KONG_ADMIN_API_URL=http://kong \
KUBE_API_URL=http://kubeapi \
KUBE_API_USER=kubeuser \
KUBE_API_PASS=kubepass \
poetry run python main.py
```

Testing:

```sh
SYNC_INTERVAL=1000 \
DATA_PLANE=test-dp \
poetry run coverage run --branch -m pytest -s -v

poetry run coverage xml
```
