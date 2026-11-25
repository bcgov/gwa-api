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
  -e VERSION_TAG_PREFIXES="ruleset-,dev-ruleset-" \
  csitoasvalidationapi
```

## Ruleset versions

The Spectral rulesets live in the [bcgov/itk-api-governance](https://github.com/bcgov/itk-api-governance)
repository. Each ruleset version is a git tag. The tags are not built into the image: when the
container starts, `entrypoint.sh` runs `python -m csit_validation.services.ruleset_fetcher`, which
fetches the matching tags into `GITHUB_TAG_CACHE_PATH`, and then starts the API. A new tag is served
after the next restart (for example `oc rollout restart`); no image build or release is needed.

For each tag, the fetcher writes the files to `<GITHUB_TAG_CACHE_PATH>/tags/<tag>/` and records the
tag's commit in `<GITHUB_TAG_CACHE_PATH>/manifest.json`. It logs each tag with its commit, and
`/health` reports them under `components.rulesets`.

If the fetch fails:

- when the cache already holds tags from an earlier fetch (the container restarted in the same pod and
  the cache is an `emptyDir`), those tags are served and a warning is logged;
- otherwise the container exits with an error and is not started, so it never serves without rulesets.
  `/readyz` also returns 503 when no ruleset versions are available.

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `VERSION_TAG_PREFIXES` | `ruleset-` | Ordered list of tag prefixes, separated by commas or spaces. Tags that start with a prefix followed by a semantic version (`v<semver>`) are fetched and served; the version is the tag without its prefix. When two tags give the same version, the tag whose prefix is listed first wins. |
| `RULESET_DIRECTORY` | `dist/spectral` | Directory within each tag that holds the ruleset files. A ruleset's name is its path within this directory without the extension, e.g. `dist/spectral/sdx/ruleset.yaml` is `sdx/ruleset`. |
| `GITHUB_TAG_CACHE_PATH` | `/tmp/ruleset_cache` in the image | Where the tags are fetched to and served from. Must be writable by the container user; in OpenShift, mount an `emptyDir` here or at `/tmp`. |
| `RULESET_REPO_URL` | `https://github.com/bcgov/itk-api-governance.git` | Repository to fetch the tags from. The container needs egress to it. |
| `RULESET_FETCH_TIMEOUT_SECONDS` | `45` | Time limit for each git command during the startup fetch. Keep the total within the startup probe's budget. |

Example of prefix precedence, with `VERSION_TAG_PREFIXES="ruleset-,dev-ruleset-"` (as in the dev
environment) and the tags `ruleset-v1.1.0`, `dev-ruleset-v1.1.0` and `dev-ruleset-v1.2.0`:

| Version | Served from | Why |
|---|---|---|
| `v1.1.0` | `ruleset-v1.1.0` | Both tags give `v1.1.0`; `ruleset-` is listed before `dev-ruleset-`. |
| `v1.2.0` | `dev-ruleset-v1.2.0` | No `ruleset-v1.2.0` tag exists yet. |

This lets dev preview a ruleset version from a `dev-ruleset-` tag, and serve the published
`ruleset-` tag automatically once it is created. Published `ruleset-` tags must never be moved or
deleted, because the API Services Portal records the version it validated with.

## Tests

To run the server locally, fetch the ruleset versions you want into a local directory, then start
the service with `GITHUB_TAG_CACHE_PATH` pointing at that directory. Set `VERSION_TAG_PREFIXES` to
choose which tags are fetched and served.

```bash
export GITHUB_TAG_CACHE_PATH="$(pwd)/ruleset_cache"
export VERSION_TAG_PREFIXES="ruleset-,dev-ruleset-"

poetry run python -m csit_validation.services.ruleset_fetcher
poetry run uvicorn csit_validation.main:app --reload --port 8080
```

The unit tests don't need a fetch: they use the fixtures under `tests/unit/resources/github-cache`.

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

List rulesets for version v1.0.0
```sh
curl -s http://localhost:8080/versions/v1.0.0/rulesets | jq .
```

Validate with JSON document
```sh
curl -X POST http://localhost:8080/versions/v1.0.0/rulesets/basic-ruleset/validations \
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
