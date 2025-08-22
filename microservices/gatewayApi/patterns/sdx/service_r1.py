
from string import Template



###
### Service API
###
### - all routes are protected by mTLS
### - default 401 response for all requests
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
      - name: mtls-auth
        tags: [ns.${gateway}.${ns_qualifier}]
        config:
          error_response_code: 401
          upstream_cert_cn_header: "X-CERT-CN"
          upstream_cert_fingerprint_header: "X-CERT-FINGERPRINT"
          upstream_cert_i_dn_header: "X-CERT-I-DN"
          upstream_cert_s_dn_header: "X-CERT-S-DN"
          upstream_cert_serial_header: "X-CERT-SERIAL"
      - name: mtls-acl
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          certificate_header_name: X-CERT-S-DN
          allow: [ ${mtls_allow_list} ]

      - name: jwt-keycloak_1010
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          allowed_iss:
            - https://aps-jwks-upstream-jwt-api-gov-bc-ca-lab.dev.api.gov.bc.ca
          allowed_aud: ${consumer_client_id}
          header_names: [ SDX-AP-AUTH ]

      - name: oidc
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          client_secret: NOT_APPLICABLE
          client_id: NOT_APPLICABLE
          header_names: ["X-IDP-P-PERSON-PPID", "X-IDP-P-AZP-CLIENT-ID"]
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

    routes:
      - name: ${service_name}
        tags: [ns.${gateway}.${ns_qualifier}]
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
""")

def eval_service_pattern (context):
  return template.substitute(context)
