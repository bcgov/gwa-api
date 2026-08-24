# FROM golang:1.15.2 AS build
# WORKDIR /deck
# RUN git clone https://github.com/kong/deck.git
# RUN cd deck \
#  && go mod download \
#  && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o deck \
#       -ldflags "-s -w -X github.com/kong/deck/cmd.VERSION=$TAG -X github.com/kong/deck/cmd.COMMIT=$COMMIT"
FROM python:3.13-alpine3.22

RUN mkdir /.kube

RUN chmod ugo+rw /.kube

WORKDIR /app

RUN apk add build-base libffi-dev openssl openssl-dev curl

# TARGETARCH is amd64/arm64 from BuildKit (docker buildx / compose build).
# Default amd64 for classic `docker build` where automatic platform ARGs are empty.
ARG TARGETARCH=amd64

RUN curl -fLO "https://storage.googleapis.com/kubernetes-release/release/$(curl -fsS https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/${TARGETARCH}/kubectl" && \
    chmod +x kubectl; mv kubectl /usr/local/bin/.

#COPY --from=build /deck/deck /usr/local/bin

# gwa api (kong 2) — v1.5.0 has no linux_arm64 release
RUN if [ "$TARGETARCH" = "amd64" ]; then \
      curl -fsSL https://github.com/kong/deck/releases/download/v1.5.0/deck_1.5.0_linux_amd64.tar.gz -o deck.tar.gz && \
      tar -xf deck.tar.gz -C /tmp && \
      cp /tmp/deck /usr/local/bin/deck_kong2_150; \
    else \
      echo "Skipping deck_kong2_150 on ${TARGETARCH} (no upstream arm64 release for v1.5.0)"; \
    fi

# gwa api (kong 3)
RUN curl -fsSL https://github.com/Kong/deck/releases/download/v1.53.1/deck_1.53.1_linux_${TARGETARCH}.tar.gz -o deck.tar.gz && \
   tar -xf deck.tar.gz -C /tmp && \
   cp /tmp/deck /usr/local/bin/deck && \
   cp /tmp/deck /usr/local/bin/deck_kong3_1531 && \
   rm -f deck.tar.gz

RUN python -m pip install --upgrade pip

RUN cd /tmp && \
    curl -sSL https://install.python-poetry.org > get-poetry.py && \
    POETRY_HOME=/opt/poetry python get-poetry.py --version 1.8.5 && \
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
ENV DECK_CLI=deck

ENTRYPOINT ["./entrypoint.sh"]
