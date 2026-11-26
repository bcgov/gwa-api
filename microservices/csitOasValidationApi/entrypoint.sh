#!/bin/sh
set -e

# Fetch the Spectral ruleset tags into GITHUB_TAG_CACHE_PATH before the API starts.
# Exits non-zero, and so stops the container, when nothing could be fetched and nothing is cached.
python -m csit_validation.services.ruleset_fetcher

exec uvicorn csit_validation.main:app --host 0.0.0.0 --port 8080
