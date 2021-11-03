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
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
```

#### Requirements

```bash
cd /api-serv-infra/dockerfiles/healthapi
poetry env use 3.9
poetry install
```
