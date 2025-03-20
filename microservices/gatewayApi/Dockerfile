# FROM golang:1.15.2 AS build
# WORKDIR /deck
# RUN git clone https://github.com/kong/deck.git
# RUN cd deck \
#  && go mod download \
#  && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o deck \
#       -ldflags "-s -w -X github.com/kong/deck/cmd.VERSION=$TAG -X github.com/kong/deck/cmd.COMMIT=$COMMIT"
FROM python:3.11-alpine3.20

RUN mkdir /.kube

RUN chmod ugo+rw /.kube

WORKDIR /app

RUN apk add build-base libffi-dev openssl openssl-dev curl

RUN curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl; mv kubectl /usr/local/bin/.

#COPY --from=build /deck/deck /usr/local/bin

# gwa api (kong 2)
RUN curl -sL https://github.com/kong/deck/releases/download/v1.5.0/deck_1.5.0_linux_amd64.tar.gz -o deck.tar.gz && \
   tar -xf deck.tar.gz -C /tmp && \
   cp /tmp/deck /usr/local/bin/deck_kong2_150

# gwa api (kong 3)
RUN curl -sL https://github.com/Kong/deck/releases/download/v1.45.0/deck_1.45.0_linux_amd64.tar.gz -o deck.tar.gz && \
   tar -xf deck.tar.gz -C /tmp && \
   cp /tmp/deck /usr/local/bin/deck_kong3_1450

RUN python -m pip install --upgrade pip
# FIX: No module named 'urllib3.packages.six'
RUN pip uninstall urllib3 && pip install urllib3
RUN cd /tmp && \
    curl -sSL https://install.python-poetry.org > get-poetry.py && \
    POETRY_HOME=/opt/poetry python get-poetry.py --version 1.8.2 && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false
COPY pyproject.toml /tmp/
COPY poetry.lock /tmp/
RUN cd /tmp && poetry install --no-root --no-dev

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 2000

ENV DECK_ANALYTICS=off
ENV DECK_CLI=deck_kong3_1450

ENTRYPOINT ["./entrypoint.sh"]
