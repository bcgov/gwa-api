# FROM golang:1.15.2 AS build
# WORKDIR /deck
# RUN git clone https://github.com/kong/deck.git
# RUN cd deck \
#  && go mod download \
#  && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o deck \
#       -ldflags "-s -w -X github.com/kong/deck/cmd.VERSION=$TAG -X github.com/kong/deck/cmd.COMMIT=$COMMIT"

FROM python:3.8.15-alpine3.16

RUN mkdir /.kube

RUN chmod ugo+rw /.kube

WORKDIR /app

RUN apk add build-base libffi-dev openssl openssl-dev curl

RUN curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl; mv kubectl /usr/local/bin/.

#COPY --from=build /deck/deck /usr/local/bin

# gwa api v1/v2
RUN curl -sL https://github.com/kong/deck/releases/download/v1.5.0/deck_1.5.0_linux_amd64.tar.gz -o deck.tar.gz && \
   tar -xf deck.tar.gz -C /tmp && \
   cp /tmp/deck /usr/local/bin/

# gwa api v3
RUN curl -sL https://github.com/Kong/deck/releases/download/v1.27.1/deck_1.27.1_linux_amd64.tar.gz -o deck.tar.gz && \
   tar -xf deck.tar.gz -C /tmp && \
   cp /tmp/deck /usr/local/bin/deck127

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 2000

ENV DECK_ANALYTICS=off

ENTRYPOINT ["./entrypoint.sh"]
