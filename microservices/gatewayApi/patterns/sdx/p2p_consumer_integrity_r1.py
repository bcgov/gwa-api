
from string import Template



###
### Application API
###
### - non-mTLS route in for consumers
### - validate user token with DPoP
### - add kong-upstream-jwt for signing
### - mTLS route for upstream service to peer access point
###
template = Template("""
_format_version: "3.0"
services:
  - name: ${service_name}
    url: ${upstream_uri}
    tags: [ns.${gateway}.${ns_qualifier}]
    retries: 0
    tls_verify: true
    routes:
      - name: ${service_name}-OPTIONS
        tags: [ns.${gateway}.${ns_qualifier}, sdx]
        hosts:
          - ${route_host}
        paths:
          - ${route_path}
        methods:
          - OPTIONS
        strip_path: false
        https_redirect_status_code: 426
        path_handling: v0
        request_buffering: true
        response_buffering: true
                    
      - name: ${service_name}
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
        strip_path: false
        https_redirect_status_code: 426
        path_handling: v0
        request_buffering: true
        response_buffering: true
    plugins:
      - name: trust-sign
        tags: [ns.${gateway}.${ns_qualifier}]
        config:
          private_key_location: "/etc/secrets/sdx-edge-signing-cert/tls.key"
          keyid: ${edge_kid}
          alg: ES256
          hash_alg: sha256
          signature_header_key: X-Edge-Token
          signature_label: sig1
          signature_input: '("@authority")'
          direction: request

      - name: rate-limiting
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          policy: local
          fault_tolerant: true
          second: 50
          limit_by: ip

      - name: cors
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          origins: ["*"]
          methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
          headers: ["Accept", "Accept-Version", "Content-Length", "Content-Type", "Authorization", "X-Client-Id", "X-Sdx-Ap-Sign", "Content-Digest", "Dpop"]

      - name: request-transformer
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          replace:
            headers:
              - "Host:${provider_endpoint}"
          add:
            headers:
              - "X-Client-Id:${consumer_uri}"
                    
      - name: response-transformer
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          remove:
            headers:
              - Set-Cookie
              - Server
              - Via
              - X-Powered-By
""")

def eval_p2p_consumer_pub_pattern (context):
  return template.substitute(context)
