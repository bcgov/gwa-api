FROM python:3.8.15-alpine3.16

RUN mkdir /.kube

RUN chmod ugo+rw /.kube

WORKDIR /app

RUN apk add build-base libffi-dev openssl curl jq

RUN curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl; mv kubectl /usr/local/bin/.

RUN python -m pip install --upgrade pip

RUN cd /tmp && \
    curl -sSL https://install.python-poetry.org > get-poetry.py && \
    POETRY_HOME=/opt/poetry python get-poetry.py --version 1.3.1 && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

COPY pyproject.toml /tmp/

COPY poetry.lock /tmp/

RUN cd /tmp && poetry install --no-root --no-dev

COPY . /app

CMD ["python", "main.py"]