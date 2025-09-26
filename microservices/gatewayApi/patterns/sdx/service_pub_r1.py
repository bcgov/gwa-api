
from string import Template



###
### Service Pub API
###
### - basic cors
###
template = Template("""
_format_version: "3.0"
services:
  - name: ${service_name}
    url: ${upstream_uri}
    tags: [ns.${gateway}.${ns_qualifier}]
    retries: 0
    tls_verify: false
    plugins:
      - name: cors
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          origins: ["*"]
          methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
          headers: ["Accept", "Accept-Version", "Content-Length", "Content-Type", "Authorization", "X-Client-Id", "X-Sdx-Ap-Sign", "DPoP"]

    routes:
      - name: ${service_name}.API
        tags: [ns.${gateway}.${ns_qualifier}, sdx]
        hosts:
          - ${route_host}
        paths:
          - ${route_path}
        methods:
          - GET
          - POST
          - PUT
          - DELETE
          - OPTIONS
        strip_path: true
        https_redirect_status_code: 426
        path_handling: v0
        request_buffering: true
        response_buffering: true
          
      - name: ${service_name}.SIGNED
        tags: [ns.${gateway}.${ns_qualifier}, sdx]
        hosts:
          - ${route_host}
        paths:
          - ${route_path}
        headers:
          "X-Client-Id": [ ${consumer_uri} ]
          "Accept": ["application/jws+jwt"]
        methods:
          - GET
          - POST
          - PUT
          - DELETE
        strip_path: true
        https_redirect_status_code: 426
        path_handling: v0
        request_buffering: true
        response_buffering: true
        plugins:
        - name: response-signer
          tags: [ns.${gateway}.${ns_qualifier}]
          enabled: true
          config:
            public_key_location: /etc/secrets/kong-upstream-jwt/tls.crt
            private_key_location: /etc/secrets/kong-upstream-jwt/tls.key
            key_id: "aps-kong-gateway"
            issuer: "https://aps-jwks-upstream-jwt-api-gov-bc-ca-lab.dev.api.gov.bc.ca"

""")

def eval_service_pub_pattern (context):
  return template.substitute(context)
