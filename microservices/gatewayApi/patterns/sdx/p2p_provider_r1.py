
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
        enabled: false
        config:
          allowed_iss:
            - https://aps-jwks-upstream-jwt-api-gov-bc-ca-lab.dev.api.gov.bc.ca
          allowed_aud: ${consumer_client_id}
          header_names: [ SDX-AP-AUTH ]

      - name: jwt-keycloak
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          allowed_iss:
            - ${openid_issuer}
          allowed_aud: "${openid_audience}"
          scope: [ ${openid_scope} ]

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

      - name: trust-verify-signature
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          direction: request
          manifest_type: signature-only
          signature_header_key: X-Edge-Token
                    
    routes:
      - name: ${service_name}
        tags: [ns.${gateway}.${ns_qualifier}, sdx]
        hosts:
          - ${route_host}
        paths:
          - ${route_path}
        headers:
          "X-Client-Id": [ ${consumer_uri} ]                    
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
                    
      - name: ${service_name}-SIGNED
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

def eval_p2p_provider_pattern (context):
  mtls_allow_list = context.get("mtls_allow_list", "")
  # WORKAROUND - Seems like NGINX Client Cert does not include spaces
  # when separating the DN attributes
  # if mtls_allow_list has commas, then create two quoted values - one
  # with a ", " and the other with just a ","
  if "," in mtls_allow_list:
    mtls_allow_list = f'{mtls_allow_list.replace(", ", ",")}, {mtls_allow_list}'
  else:
    mtls_allow_list = f'{mtls_allow_list}'
  context["mtls_allow_list"] = mtls_allow_list
  return template.substitute(context)
