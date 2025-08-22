
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
      - name: ${service_name}
        tags: [ns.${gateway}.${ns_qualifier}]
        hosts:
          - ${route_host}
        paths:
          - ${route_path}
        methods:
          - GET
        strip_path: false
        https_redirect_status_code: 426
        path_handling: v0
        request_buffering: true
        response_buffering: true
    plugins:
      - name: openid-authzen
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          # lua_ssl_trusted_certificate has to have the CA's - otherwise "unable to get local issuer certificate"
          target_url: https://ping.api.gov.bc.ca
          json_locator: []
          # subject_claim: "sub"
          # resource_type: "service_name|route_name|uri_path"
          # action_name: "read"

      - name: kong-upstream-jwt
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          header: "SDX-AP-AUTH"
          include_credential_type: true
          key_id: aps-kong-gateway
          issuer: https://aps-jwks-upstream-jwt-api-gov-bc-ca-lab.dev.api.gov.bc.ca

      # - name: oidc
      #   tags: [ns.gw-0a524]
      #   enabled: true
      #   config:
      #     client_id: gw-94b7c-dpop
      #     bearer_only: "on"
      #     bearer_jwt_auth_enable: "on"
      #     discovery: https://sdx-authz-apps-gov-bc-ca-lab.apps.gov.bc.ca/auth/realms/sdx/.well-known/openid-configuration
""")

def eval_application_pattern (context):
  return template.substitute(context)
