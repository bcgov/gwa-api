
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
      strip_path: true
      https_redirect_status_code: 426
      path_handling: v0
      request_buffering: true
      response_buffering: true
""")

def eval_service_pattern (context):
  return template.substitute(context)
