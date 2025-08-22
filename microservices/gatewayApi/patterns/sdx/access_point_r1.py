
from string import Template



###
### Access Point
###
### - all routes are protected by mTLS
### - default 401 response for all requests
###
template = Template("""
_format_version: "3.0"
services:
  - name: ${service_name}
    url: ${upstream_uri}
    tags: [ns.${gateway}]
    plugins:
    - name: mtls-auth
      tags: [ns.${gateway}]
      config:
        error_response_code: 401
        upstream_cert_cn_header: "X-CERT-CN"
        upstream_cert_fingerprint_header: "X-CERT-FINGERPRINT"
        upstream_cert_i_dn_header: "X-CERT-I-DN"
        upstream_cert_s_dn_header: "X-CERT-S-DN"
        upstream_cert_serial_header: "X-CERT-SERIAL"
    - name: mtls-acl
      tags: [ns.${gateway}]
      enabled: true
      config:
        certificate_header_name: X-CERT-S-DN
        allow: [ ${ap_allow_list} ]
    routes:
    - name: ${service_name}.DENY
      tags: [ns.${gateway}]
      hosts:
        - ${ap_host}
      paths:
        - /
      methods:
        - GET
      strip_path: true
      https_redirect_status_code: 426
      path_handling: v0
      request_buffering: true
      response_buffering: true
      plugins:
      - name: request-termination
        tags: [ns.${gateway}]
        config:
          status_code: 401
          message: "Access Denied. Please login to access this service."

""")

def eval_pattern (context):
  return template.substitute(context)
