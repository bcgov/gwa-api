
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
    tags: [ns.${gateway}.${ns_qualifier}]
    plugins:
    - name: mtls-auth
      tags: [ns.${gateway}.${ns_qualifier}]
      enabled: false
      config:
        error_response_code: 401
        upstream_cert_cn_header: "X-CERT-CN"
        upstream_cert_fingerprint_header: "X-CERT-FINGERPRINT"
        upstream_cert_i_dn_header: "X-CERT-I-DN"
        upstream_cert_s_dn_header: "X-CERT-S-DN"
        upstream_cert_serial_header: "X-CERT-SERIAL"
    - name: request-termination
      tags: [ns.${gateway}.${ns_qualifier}]
      config:
        status_code: 401
        message: "Access Denied. Route not found."                    
    routes:
    - name: ${service_name}.DENY
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

  - name: ${service_name}.CONSOLE
    url: https://sdx-beta-api-gov-bc-ca-lab.dev.api.gov.bc.ca
    tags: [ns.${gateway}.${ns_qualifier}]
    routes:
      - name: ${service_name}.CONSOLE
        tags: [ns.${gateway}.${ns_qualifier}, sdx]
        hosts:
          - ${route_host}
        paths:
          - /console
          - /api/rd/
        methods:
          - GET
        strip_path: false
        https_redirect_status_code: 426
        path_handling: v0
        request_buffering: true
        response_buffering: true
      - name: ${service_name}.CONSOLE-DS-API
        tags: [ns.${gateway}.${ns_qualifier}, sdx]
        hosts:
          - ${route_host}
        paths:
          - /api/ds/
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
  - name: ${service_name}.AUTH
    url: https://httpbin.org
    tags: [ns.${gateway}.${ns_qualifier}]
    tls_verify: false
    routes:
    - name: ${service_name}.AUTH-OPTIONS
      tags: [ns.${gateway}.${ns_qualifier}, sdx]
      hosts:
        - ${route_host}
      paths:
        - /auth
      methods:
        - OPTIONS
      strip_path: false
      preserve_host: false
      https_redirect_status_code: 426
      path_handling: v0
      request_buffering: true
      response_buffering: true
    - name: ${service_name}.AUTH
      tags: [ns.${gateway}.${ns_qualifier}, sdx]
      hosts:
        - ${route_host}
      paths:
        - /auth
      methods:
        - POST
      strip_path: false
      preserve_host: false
      https_redirect_status_code: 426
      path_handling: v0
      request_buffering: true
      response_buffering: true
      plugins:
        - name: pre-function
          tags: [ns.${gateway}.${ns_qualifier}]
          enabled: true
          config:
            access:
              - |
                  local os = require "os"
                  local io = require "io"
                  local ssl = require('ngx.ssl')

                  local http = require "resty.http"
                  local cjson = require "cjson.safe"

                  local httpc = http.new()
                  local req_body = kong.request.get_raw_body()

                  local client_cert_path = os.getenv("KONG_CLIENT_SSL_CERT")
                  local client_key_path = os.getenv("KONG_CLIENT_SSL_CERT_KEY")
                    
                  if req_body then
                      -- Process the raw body string
                      kong.log.info("Request body: ", req_body)
                  end          

                  local function read_file(filename)
                      local file = io.open(filename, "r")
                      if not file then
                          kong.log.err("Error: Could not open file " .. filename)
                          return kong.response.exit(500, "Error: Could not open file " .. filename)
                      end
                      
                      local content = file:read("*all")  -- Read entire file
                      file:close()
                      return content
                  end

                  local config = {
                      -- Server details
                      host = "sdx-authz-apps-gov-bc-ca-lab.apps.gov.bc.ca",
                      port = 443,
                      path = "/auth/realms/sdx/protocol/openid-connect/token",
                      
                      -- Client certificate files
                      cert_file = assert(ssl.parse_pem_cert(read_file(client_cert_path))),
                      key_file = assert(ssl.parse_pem_priv_key(read_file(client_key_path))),
                      
                      -- Request data
                      post_data = req_body,
                      content_type = "application/x-www-form-urlencoded"
                  }

                  if not config.cert_file or not config.key_file then
                      kong.log.err("Failed to load certificates as cdata")
                      return kong.response.exit(500, "Failed to load certificates as cdata")
                  end
                  
                  local res, err = httpc:request_uri(
                      "https://" .. config.host .. ":" .. config.port .. config.path, 
                      {
                        method = "POST",
                        headers = {
                          ["Content-Type"] = config.content_type,
                          ["Accept"] = "application/json",
                          ["DPoP"] = kong.request.get_header("DPoP")
                        },
                        body = config.post_data,
                        ssl_verify = true,
                        ssl_client_cert = config.cert_file,
                        ssl_client_priv_key = config.key_file
                      }
                  )

                  if not res then
                      return kong.response.exit(502, "Upstream request failed: " .. (err or "unknown error"))
                  end

                  kong.response.set_header("Content-Type", res.headers["Content-Type"] or "application/json")
                  return kong.response.exit(res.status, res.body)

                                                     
    plugins:
    - name: cors
      tags: [ns.${gateway}.${ns_qualifier}]
      enabled: true
      config:
        origins:
          - "*"
        methods:
          - GET
          - POST
          - OPTIONS
        headers:
          - Accept
          - Authorization
          - Content-Type
          - If-None-Match
          - X-Client-Id
          - DPoP

  - name: ${service_name}.JWKS
    url: https://httpbin.org
    tags: [ns.${gateway}.${ns_qualifier}]
    tls_verify: false
    routes:
    - name: ${service_name}.JWKS
      tags: [ns.${gateway}.${ns_qualifier}, sdx]
      hosts:
        - ${route_host}
      paths:
        - /jwks
      methods:
        - GET
      strip_path: false
      preserve_host: false
      https_redirect_status_code: 426
      path_handling: v0
      request_buffering: true
      response_buffering: true
    plugins:
      - name: trust-registry
        tags: [ns.${gateway}.${ns_qualifier}]
        config:
          key_set: "set_123"
             
         
""")

def eval_access_point_pattern (context):
  return template.substitute(context)
