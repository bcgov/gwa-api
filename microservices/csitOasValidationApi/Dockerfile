FROM python:3.14.2-alpine3.23

WORKDIR /app

RUN apk add build-base libffi-dev openssl curl git bash nodejs npm

RUN python -m pip install --upgrade pip

# Install Spectral CLI (required for validation)
RUN npm install -g @stoplight/spectral-cli@6.14.2

RUN cd /tmp && \
    curl -sSL https://install.python-poetry.org > get-poetry.py && \
    POETRY_HOME=/opt/poetry python get-poetry.py --version 1.8.2 && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

COPY pyproject.toml /tmp/

COPY poetry.lock /tmp/

RUN cd /tmp && poetry install --no-root --no-dev

COPY . /app

RUN chmod +x /app/entrypoint.sh

# Retrieve and cache the ruleset
RUN mkdir -p /app/ruleset_tag_cache && \
    /app/checkout-ruleset-tags.sh /app/ruleset_tag_cache

ENV GITHUB_TAG_CACHE_PATH=/app/ruleset_tag_cache

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"] 