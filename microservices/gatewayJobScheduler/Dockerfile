FROM python:3.12.15-alpine3.24

# Install wheels only (no source builds, so no package setup scripts run)
ENV POETRY_INSTALLER_ONLY_BINARY=":all:"

RUN apk add --no-cache openssl && \
    python -m venv /opt/poetry && \
    /opt/poetry/bin/pip install --no-cache-dir --only-binary :all: poetry==2.2.1 && \
    ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry && \
    poetry config virtualenvs.create false

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root --without dev --no-cache

COPY . /app

CMD ["python", "main.py"]
