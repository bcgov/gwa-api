
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
    - name: mtls-acl
      tags: [ns.${gateway}.${ns_qualifier}]
      enabled: false
      config:
        certificate_header_name: X-CERT-S-DN
        allow: [ ${mtls_allow_list} ]
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
      plugins:
      - name: request-termination
        tags: [ns.${gateway}.${ns_qualifier}]
        config:
          status_code: 401
          message: "Access Denied. Route not found."

  - name: ${service_name}-CONSOLE
    url: http://sdx-demo-ui-lab-generic-api
    tags: [ns.${gateway}.${ns_qualifier}]
    routes:
      - name: ${service_name}-CONSOLE
        tags: [ns.${gateway}.${ns_qualifier}, sdx]
        hosts:
          - sdx.api.gov.bc.ca
        paths:
          - /console
        methods:
          - GET
        strip_path: true
        https_redirect_status_code: 426
        path_handling: v0
        request_buffering: true
        response_buffering: true
                    
  - name: ${service_name}-CONSOLE-DS
    url: https://api-gov-bc-ca-lab.dev.api.gov.bc.ca/
    tags: [ns.${gateway}.${ns_qualifier}]
    routes:
      - name: ${service_name}-CONSOLE-DS
        tags: [ns.${gateway}.${ns_qualifier}, sdx]
        hosts: 
        - ${route_host}
        paths:
          - /api/ds
        methods: [GET,PUT,POST,DELETE]
        strip_path: true
        preserve_host: false
                    
  - name: ${service_name}-CONSOLE-RD
    url: https://bcgov.github.io/sdx-openapi/data/lab
    tags: [ns.${gateway}.${ns_qualifier}]
    routes:
      - name: ${service_name}-CONSOLE-RD
        tags: [ns.${gateway}.${ns_qualifier}, sdx]
        hosts: 
        - ${route_host}
        paths:
          - /api/rd
        methods: [GET]
        strip_path: true
        preserve_host: false

    plugins:
    - name: pre-function
      tags: [ns.${gateway}.${ns_qualifier}]
      config:
        access:
        - |
          -- Kong pre-function to rewrite the request path for /api/rd/{id} to /{id}.json
          -- This function captures the {id} parameter and rewrites the path accordingly

          -- Get the original request path
          local original_path = ngx.var.request_uri

          -- Use a pattern to extract the {id} from the path
          local id = original_path:match("/api/rd/(.+)")

          if id then
              -- Construct the new path by appending .json to the extracted id
              -- prepend current service path
              local service = kong.router.get_service()
              
              local new_path = service.path .. "/" .. id .. ".json"

              kong.service.request.set_path(new_path)

              -- Optionally, log the path rewrite for debugging
              ngx.log(ngx.WARN, "Rewritten path from ", original_path, " to ", new_path)
          else
              -- If no id is found, log a warning (optional)
              ngx.log(ngx.WARN, "No ID found in the request path: ", original_path)
          end                    

  - name: ${service_name}-AUTH
    url: https://httpbin.org
    tags: [ns.${gateway}.${ns_qualifier}]
    tls_verify: false
    routes:
    - name: ${service_name}-AUTH
      tags: [ns.${gateway}.${ns_qualifier}, sdx]
      hosts:
        - ${route_host}
      paths:
        - /auth
      methods:
        - POST
        - OPTIONS
      strip_path: false
      preserve_host: false
      https_redirect_status_code: 426
      path_handling: v0
      request_buffering: true
      response_buffering: true
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

    - name: pre-function
      tags: [ns.${gateway}.${ns_qualifier}]
      enabled: true
      config:
        access:
          - |
              local client_cert_path = "/etc/secrets/kong-client-tls/tls.crt"
              local client_key_path = "/etc/secrets/kong-client-tls/tls.key"

              local io = require "io"
              local ssl = require('ngx.ssl')

              local http = require "resty.http"
              local cjson = require "cjson.safe"

              local httpc = http.new()
              local req_body = kong.request.get_raw_body()

              if req_body then
                  -- Process the raw body string
                  kong.log.info("Request body: ", req_body)
              end          

              local function read_file(filename)
                  local file = io.open(filename, "r")
                  if not file then
                      print("Error: Could not open file " .. filename)
                      return nil
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
                  print("Failed to load certificates as cdata")
                  return nil
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

""")

def eval_access_point_pattern (context):
  return template.substitute(context)
