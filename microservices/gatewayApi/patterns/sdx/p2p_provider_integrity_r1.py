
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

      - name: trust-verify-signature
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          direction: request
          manifest_type: signature-only
          signature_header_key: X-Edge-Token

      - name: trust-sign
        tags: [ns.${gateway}.${ns_qualifier}]
        config:
          direction: response
          private_key_location: "/etc/secrets/sdx-edge-signing-cert/tls.key"
          jwks_uri: "https://sdx-min-citz-jwks-api-gov-bc-ca-lab.dev.api.gov.bc.ca"
          keyid: ${edge_kid}
          alg: ES256
          hash_alg: sha256
          signature_header_key: X-Edge-Token

      - name: request-transformer
        tags: [ns.${gateway}.${ns_qualifier}]
        enabled: true
        config:
          remove:
            headers:
              - Cookie
              - Forwarded
              - Priority
              - Sec-Ch-Ua
              - Sec-Ch-Ua-Mobile
              - Sec-Ch-Ua-Platform
              - Sec-Fetch-Dest
              - Sec-Fetch-Mode
              - Sec-Fetch-Site
              - Sec-Fetch-User
              - Upgrade-Insecure-Requests
              - User-Agent
              - Via
              - X-Forwarded-Path
              - X-Forwarded-Port
              - X-Forwarded-Prefix
              - X-Real-Ip

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


""")

def eval_p2p_provider_integrity_pattern (context):
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
