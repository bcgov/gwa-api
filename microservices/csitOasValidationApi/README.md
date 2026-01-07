# CSIT OAS Validation API

## Description

This API validates OAS files.

## Requirements.

Python >= 3.7

#### Docker

```bash
docker build --tag csitoasvalidationapi .

docker run -ti --rm \
  -p 8080:8080 \
  -e LOG_LEVEL=DEBUG \
  csitoasvalidationapi
```


## Tests

To run the server, please execute the following from the root directory:

```bash
env GITHUB_TOKEN=<your GitHub token> GITHUB_REPO_OWNER=bcgov GITHUB_REPO_NAME=csit-api-governance-spectral-style-guide poetry run uvicorn csit_validation.main:app --reload --port 8080
```

and open your browser at `http://localhost:8080/docs/` to see the docs.

WARNING: Running the service without a GITHUB_TOKEN can cause performance issues and result in a 503 due to GitHub rate limiting.

Testing:

```sh
poetry run pytest -v -s --log-cli-level=DEBUG -k
poetry run coverage run --branch -m pytest -s
poetry run coverage xml
``` 

List all available versions (sorted newest first)
```sh
curl -s http://localhost:8080/versions | jq .

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