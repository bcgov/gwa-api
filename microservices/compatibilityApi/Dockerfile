FROM python:3.12.9-alpine3.21

WORKDIR /app

RUN apk add build-base libffi-dev openssl curl

# Install deck
RUN curl -sL https://github.com/kong/deck/releases/download/v1.35.0/deck_1.35.0_linux_amd64.tar.gz -o deck.tar.gz && \
    tar -xf deck.tar.gz -C /tmp && \
    mv /tmp/deck /usr/local/bin/ && \
    rm deck.tar.gz

RUN python -m pip install --upgrade pip

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

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"] 