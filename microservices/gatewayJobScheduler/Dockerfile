FROM python:3.12.15-alpine3.24

WORKDIR /app

RUN apk add build-base libffi-dev openssl curl

RUN python -m pip install --upgrade pip

RUN cd /tmp && \
    curl -sSL https://install.python-poetry.org > get-poetry.py && \
    POETRY_HOME=/opt/poetry python get-poetry.py --version 2.2.1 && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

COPY pyproject.toml /tmp/

COPY poetry.lock /tmp/

RUN cd /tmp && poetry install --no-root --without dev

COPY . /app

CMD ["python", "main.py"]
