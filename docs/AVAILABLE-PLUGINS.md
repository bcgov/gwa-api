Current list of plugins available on the API Gateway.

> NOTE: The `httplog` is not available for individual teams to use as it is used at a global level to feed logs to other systems for audit/monitoring/etc.

> If there are other plugins that you would like to have added to the Gateway, please reach out to us at our Rocket.Chat channel `#aps-ops`.

```json
    "available_on_server": {
      "basic-auth": true,
      "ip-restriction": true,
      "request-transformer": true,
      "response-transformer": true,
      "request-size-limiting": true,
      "rate-limiting": true,
      "response-ratelimiting": true,
      "syslog": true,
      "loggly": true,
      "datadog": true,
      "ldap-auth": true,
      "statsd": true,
      "bot-detection": true,
      "aws-lambda": true,
      "request-termination": true,
      "azure-functions": true,
      "zipkin": true,
      "pre-function": true,
      "post-function": true,
      "prometheus": true,
      "proxy-cache": true,
      "session": true,
      "acme": true,
      "grpc-web": true,
      "grpc-gateway": true,
      "kong-spec-expose": true,
      "jwt-keycloak": true,
      "referer": true,
      "bcgov-gwa-endpoint": true,
      "gwa-ip-anonymity": true,
      "oidc": true,
      "jwt": true,
      "acl": true,
      "correlation-id": true,
      "cors": true,
      "oauth2": true,
      "tcp-log": true,
      "udp-log": true,
      "file-log": true,
      "http-log": true,
      "key-auth": true,
      "hmac-auth": true
    }
 ```
