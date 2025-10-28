
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

      - name: oidc
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          client_secret: NOT_APPLICABLE
          client_id: NOT_APPLICABLE
          header_names: ["X-IDP-C-PERSON-PPID", "X-IDP-C-AZP-CLIENT-ID"]
          bearer_jwt_auth_allowed_auds: [ ${openid_audience} ]
          unauth_action: deny
          bearer_only: "yes"
          use_jwks: "yes"
          bearer_jwt_auth_enable: "yes"
          discovery: ${openid_issuer}/.well-known/openid-configuration
          header_claims: ["sub", "azp"]

          # scope and validate_scope do nothing when bearer_jwt_auth_enable is "yes"
          # scope: ${openid_scope}
          # validate_scope: "yes"
          disable_userinfo_header: "yes"
          disable_id_token_header: "yes"

      - name: kong-upstream-jwt
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          header: "SDX-AP-AUTH"
          include_credential_type: true
          key_id: aps-kong-gateway
          issuer: https://aps-jwks-upstream-jwt-api-gov-bc-ca-lab.dev.api.gov.bc.ca

      - name: request-transformer
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          add:
            headers:
              - "X-Client-Id:${consumer_uri}"

      - name: dpop
        tags: [ns.${gateway}.${ns_qualifier}]
        config:
          allowed_algorithms: [ES256]
          max_age: 60
          clock_skew: 60
          nonce_cache_ttl: 300

      - name: trust-verify-digest
        tags: [ns.${gateway}.${ns_qualifier}]
        config:
          direction: request

      - name: trust-sign
        tags: [ns.${gateway}.${ns_qualifier}]
        config:
          signing_key_location: "/etc/secrets/sdx-edge-signing-cert/tls.key"
          keyid: sdx-gw-edge
          algorithm: sha512
          signature_label: sig1
          signature_input: "(@authority, @path)"
          direction: response

      - name: trust-timestamp
        tags: [ns.${gateway}.${ns_qualifier}]
        config:
          policy_oid: "1.2.1.2.1"
          endpoint_url: "https://freetsa.org/tsr"

      - name: trust-ledger
        tags: [ns.${gateway}.${ns_qualifier}]
        config:
          provider: rekor
          endpoint_url: "https://rekor.sigstore.dev"

      # - name: oidc
      #   tags: [ns.gw-0a524]
      #   enabled: true
      #   config:
      #     client_id: gw-94b7c-dpop
      #     bearer_only: "on"
      #     bearer_jwt_auth_enable: "on"
      #     discovery: https://sdx-authz-apps-gov-bc-ca-lab.apps.gov.bc.ca/auth/realms/sdx/.well-known/openid-configuration
""")

def eval_p2p_consumer_pattern (context):
  return template.substitute(context)
