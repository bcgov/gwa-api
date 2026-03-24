FROM python:3.14.3-alpine3.23 AS builder

WORKDIR /build

RUN apk add --no-cache build-base libffi-dev curl

RUN curl -sL https://github.com/smallstep/cli/releases/download/v0.30.0/step_linux_0.30.0_amd64.tar.gz -o /tmp/step.tar.gz && \
    tar -xf /tmp/step.tar.gz --strip-components=1 -C /tmp && \
    mv /tmp/bin/step /usr/local/bin/step && \
    rm /tmp/step.tar.gz

RUN pip install --no-cache-dir poetry==1.8.2

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create true && \
    poetry config virtualenvs.in-project true && \
    poetry install --no-root --no-dev

# --- runtime ---

FROM python:3.14.3-alpine3.23 AS runtime

WORKDIR /app

RUN apk add --no-cache openssl ca-certificates

COPY --from=builder /usr/local/bin/step /usr/local/bin/step
COPY --from=builder /build/.venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY . /app

RUN chmod +x /app/entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
