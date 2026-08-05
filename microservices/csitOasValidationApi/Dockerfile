# BUILD STAGE
FROM python:3.14.2-alpine3.23 AS builder

WORKDIR /build

# Install build dependencies
RUN apk add --no-cache build-base libffi-dev openssl curl git bash nodejs npm

RUN python -m pip install --upgrade pip

# Install Spectral CLI (required for validation). Pin the rulesets package
# separately because spectral-cli declares it as ">=1" and newer transitive
# releases can change validation behaviour without changing the CLI version.
ARG SPECTRAL_CLI_VERSION=6.14.2
ARG SPECTRAL_RULESETS_VERSION=1.22.2
RUN npm install -g \
      "@stoplight/spectral-cli@${SPECTRAL_CLI_VERSION}" \
      "@stoplight/spectral-rulesets@${SPECTRAL_RULESETS_VERSION}" && \
    test "$(node -p "require('/usr/local/lib/node_modules/@stoplight/spectral-rulesets/package.json').version")" = \
      "${SPECTRAL_RULESETS_VERSION}"

# Install Poetry
RUN cd /tmp && \
    curl -sSL https://install.python-poetry.org > get-poetry.py && \
    POETRY_HOME=/opt/poetry python get-poetry.py --version 1.8.2 && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

# Install Python dependencies
COPY pyproject.toml /tmp/
COPY poetry.lock /tmp/
RUN cd /tmp && poetry install --no-root --no-dev

# Retrieve and cache the ruleset
COPY checkout-ruleset-tags.sh /build/
RUN chmod +x /build/checkout-ruleset-tags.sh && \
    mkdir -p /build/ruleset_tag_cache && \
    /build/checkout-ruleset-tags.sh /build/ruleset_tag_cache

# RUNTIME STAGE
FROM python:3.14.2-alpine3.23

WORKDIR /app

# Install only runtime dependencies
# nodejs is needed for Spectral CLI to run
RUN apk add --no-cache libffi openssl nodejs

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages

# Copy Python entry point scripts (uvicorn, etc.) but exclude build tools
# First, copy all scripts, then we'll remove poetry if it exists
COPY --from=builder /usr/local/bin /usr/local/bin
RUN rm -f /usr/local/bin/poetry 2>/dev/null || true

# Copy Spectral CLI from builder
COPY --from=builder /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=builder /usr/local/bin/spectral /usr/local/bin/spectral

# Copy ruleset cache from builder
COPY --from=builder /build/ruleset_tag_cache /app/ruleset_tag_cache

# Copy application code
COPY . /app

RUN chmod +x /app/entrypoint.sh

ENV GITHUB_TAG_CACHE_PATH=/app/ruleset_tag_cache

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
