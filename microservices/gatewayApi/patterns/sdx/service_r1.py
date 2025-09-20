
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
          headers: ["Accept", "Accept-Version", "Content-Length", "Content-Type", "Authorization", "X-Client-Id", "X-Sdx-Ap-Sign"]

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

    routes:
      - name: ${service_name}.OPTIONS
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
        plugins:
        - name: jwt-keycloak
          tags: [ns.${gateway}.${ns_qualifier}]
          enabled: false
          config:
            allowed_iss:
              - ${openid_issuer}
            allowed_aud: "${openid_audience}"
            scope: [ ${openid_scope} ]
        - name: oidc
          tags: [ns.${gateway}.${ns_qualifier}]
          enabled: false
          config:
            client_secret: NOT_APPLICABLE
            client_id: NOT_APPLICABLE
            discovery: ${openid_issuer}/.well-known/openid-configuration                    
            
      - name: ${service_name}.API
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
        strip_path: true
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

                  local client_cert_path = os.getenv("KONG_CLIENT_SSL_CERT")
                  local client_key_path = os.getenv("KONG_CLIENT_SSL_CERT_KEY")


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
                      kong.log.info("Failed to load certificates as cdata")
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
                    
      - name: ${service_name}.SIGNED
        tags: [ns.${gateway}.${ns_qualifier}, sdx]
        hosts:
          - ${route_host}
        paths:
          - ${route_path}
        headers:
          "X-SDX-AP-SIGN": ["YES"]
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

def eval_service_pattern (context):
  return template.substitute(context)
