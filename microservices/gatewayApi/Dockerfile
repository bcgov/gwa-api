FROM python:3.8-alpine

WORKDIR /app

RUN apk add build-base libffi-dev openssl openssl-dev curl

RUN curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl; mv kubectl /usr/local/bin/.

RUN curl -sL https://github.com/kong/deck/releases/download/v1.2.0/deck_1.2.0_linux_amd64.tar.gz -o deck.tar.gz && \
    tar -xf deck.tar.gz -C /tmp && \
    cp /tmp/deck /usr/local/bin/

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 2000

ENV DECK_ANALYTICS=off

ENTRYPOINT ["./entrypoint.sh"]
