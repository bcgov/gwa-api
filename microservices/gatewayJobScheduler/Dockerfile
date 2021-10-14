FROM python:3.7.12

WORKDIR /app

RUN apt-get -y update

RUN apt-get -y install curl jq

RUN curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl; mv kubectl /usr/local/bin/.

RUN python -m pip install --upgrade pip

RUN cd /tmp && \
    curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py > get-poetry.py && \
    POETRY_HOME=/opt/poetry python get-poetry.py --version 1.0.8 && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

COPY pyproject.toml /tmp/

COPY poetry.lock /tmp/

RUN cd /tmp && poetry install --no-root

COPY . /app

CMD ["python", "main.py"]