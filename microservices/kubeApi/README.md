# GWA Kubernetes API

## Description

This API manages resources in Kubernetes environment.

## Getting Started

### Dependencies

- Docker
- Kubernetes

### Installation

#### Poetry

```bash
brew update
brew install pyenv
pyenv install 3.9
pyenv global 3.9
curl -sSL https://install.python-poetry.org | python3 -
```

#### Requirements

```bash
poetry env use 3.9 # (optional)
poetry install
```

#### Docker

```
docker build --tag kubeapi .

docker run -ti --rm \
  -p 8080:8080 \
  -e LOG_LEVEL=DEBUG \
  -e ACCESS_USER=kubeadmin \
  -e ACCESS_SECRET=$PASS \
  -e DEFAULT_DATA_PLANE=dp-silver-kong-proxy \
  -v ${HOME}/.kube:/root/.kube \
  -v `pwd`/_tmp:/tmp \
  kubeapi

```

### Development

Locally running:

```sh
ACCESS_USER=kubeuser ACCESS_SECRET=s3cret \
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

Testing:

```sh
ACCESS_USER=kubeuser ACCESS_SECRET=s3cret \
poetry run coverage run --branch -m pytest -s

poetry run coverage xml
```
