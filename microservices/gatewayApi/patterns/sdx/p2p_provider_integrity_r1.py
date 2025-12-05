
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
      - name: trust-sign
        tags: [ns.${gateway}.${ns_qualifier}]
        config:
          private_key_location: "/etc/secrets/sdx-edge-signing-cert/tls.key"
          keyid: ${edge_kid}
          alg: ES256
          hash_alg: sha256
          signature_header_key: X-Signature
          signature_label: sig1
          signature_input: '("@authority")'
          direction: response
   
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
