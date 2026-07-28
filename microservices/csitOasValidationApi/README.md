# CSIT OAS Validation API

## Description

This API validates OAS files.

## Requirements.

Python 3.14
Spectral 6.14.2

### Installation

#### Python 3.14
This project requires Python 3.14.

Install required packages
```bash
sudo apt update
sudo apt install -y build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev curl git libffi-dev
```
Install pyenv
```bash
curl https://pyenv.run | bash
```
Add pyenv to your shell (run once):
```bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc
```
Install Python 3.14

```bash
pyenv install 3.14.0
```

Set it for this project

```bash
cd microservices/csitOasValidationApi
```

Verify the version:

```bash
python --version   # Should show Python 3.14.0
```

#### Poetry
Install Poetry
```bash
curl -sSL https://install.python-poetry.org | python3 -
poetry config keyring.enabled false
poetry env use 3.14
poetry install
```

#### Node and NPM
Install Node and NPM (required by Spectral)
Check if node and npm are already installed
```bash
node --version
npm --version
```

If Node and NPM need to be installed
```bash
sudo apt update
sudo apt install nodejs npm
```

#### Spectral
Install Stoplight Spectral
Requires 6.0.0 or greater
```bash
sudo npm install -g \
  @stoplight/spectral-cli@6.14.2 \
  @stoplight/spectral-rulesets@1.22.2
spectral --version
```

#### Docker
```bash
sudo apt install docker.io
sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker
```

#### Docker

```bash
docker build --tag csitoasvalidationapi .

docker run -ti --rm \
  -p 8080:8080 \
  -e LOG_LEVEL=DEBUG \
  csitoasvalidationapi
```

## Tests

To run the server, you will need to check out the ruleset versions you
want to be available to the service in a local directory and set the GITHUB_TAG_CACHE_PATH
environment varable to the root of the directory, before starting the service.

```bash
./checkout-ruleset-tags.sh ruleset_tag_cache
```

```bash
export GITHUB_TAG_CACHE_PATH="$(realpath -m ./ruleset_tag_cache)"

poetry run uvicorn csit_validation.main:app --reload --port 8080
```

and open your browser at `http://localhost:8080/docs/` to see the docs.

Testing:

```sh
poetry run pytest -v -s --log-cli-level=DEBUG
poetry run coverage run --branch -m pytest -s
poetry run coverage xml
``` 

List all available versions (sorted newest first)
```sh
curl -s http://localhost:8080/versions | jq .
```

List rulesets for version v0.1.0-test
```sh
curl -s http://localhost:8080/versions/v0.1.0-test/rulesets | jq .
```

Validate with JSON document
```sh
curl -X POST http://localhost:8080/versions/v0.1.0-test/rulesets/basic-ruleset/validations \
-H "Content-Type: application/json" \
-d '{
  "openapi": "3.1.0",
  "info": {
    "title": "Test API",
    "version": "1.0.0"
  },
  "paths": {
    "/users": {
      "get": {
        "summary": "List users"
      }
    }
  }
}' \
| jq .
```
