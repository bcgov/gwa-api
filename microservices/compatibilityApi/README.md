# GWA Compatibility API

## Description

This API validates Kong Gateway configuration files.

## Getting Started

### Dependencies

- Docker
- Python 3.12

### Installation

#### Poetry

```bash
brew update
brew install pyenv
pyenv install 3.12
pyenv global 3.12
curl -sSL https://install.python-poetry.org | python3 -
```

#### Requirements

```bash
poetry env use 3.12 # (optional)
poetry install
```

#### Docker

```bash
docker build --tag compatibilityapi .

docker run -ti --rm \
  -p 8080:8080 \
  -e LOG_LEVEL=DEBUG \
  compatibilityapi
```

### Development

Locally running:

```sh
poetry run uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

Testing:

```sh
poetry run coverage run --branch -m pytest -s
poetry run coverage xml
``` 

Test with a local file:

```sh
curl -X POST http://localhost:8080/config \
  -H "Content-Type: application/json" \
  -d "$(cat test.yaml | python3 -c 'import sys, yaml, json; print(json.dumps(yaml.safe_load(sys.stdin)))')"
```