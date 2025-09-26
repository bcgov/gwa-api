
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
          headers: ["Accept", "Accept-Version", "Content-Length", "Content-Type", "Authorization", "X-Client-Id", "X-Sdx-Ap-Sign", "DPoP"]

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

                  local client_cert_path = os.getenv("KONG_CLIENT_SSL_CERT")
                  local client_key_path = os.getenv("KONG_CLIENT_SSL_CERT_KEY")

                  local function urlencode(str)
                      if not str then return "" end
                      str = tostring(str)
                      str = string.gsub(str, "([^%w%.%- ])", function(c)
                          return string.format("%%%02X", string.byte(c))
                      end)
                      str = string.gsub(str, " ", "+")
                      return str
                  end

                  local function read_file(filename)
                      local file = io.open(filename, "r")
                      if not file then
                          kong.log.err("Error: Could not open file " .. filename)
                          return kong.response.exit(500, "Error: Could not open file " .. filename)
                      end
                      
                      local content = file:read("*all")
                      file:close()
                      return content
                  end

                  local config = {
                      host = "sdx-authz-apps-gov-bc-ca-lab.apps.gov.bc.ca",
                      port = 443,
                      path = "/auth/realms/sdx/protocol/openid-connect/token/introspect",
                      
                      cert_file = assert(ssl.parse_pem_cert(read_file(client_cert_path))),
                      key_file = assert(ssl.parse_pem_priv_key(read_file(client_key_path))),
                      
                      client_id = "gw-introspection",
                  }

                  local data = {
                      client_id = config.client_id,
                      token = kong.request.get_header("Authorization"):match("Bearer%s+(.+)"),
                      token_type_hint = "access_token"
                  }

                  local encoded_body = ""
                  local first = true
                  for key, value in pairs(data) do
                      if not first then
                          encoded_body = encoded_body .. "&"
                      end
                      encoded_body = encoded_body .. urlencode(key) .. "=" .. urlencode(value)
                      first = false
                  end

                  if not config.cert_file or not config.key_file then
                      kong.log.err("Failed to load certificates as cdata")
                      return kong.response.exit(500, "Failed to load certificates as cdata")
                  end

                  local res, err = httpc:request_uri(
                      "https://" .. config.host .. ":" .. config.port .. config.path, 
                      {
                        method = "POST",
                        headers = {
                          ["Content-Type"] = 'application/x-www-form-urlencoded',
                          ["Accept"] = "application/jwt",
                        },
                        body = encoded_body,
                        ssl_verify = true,
                        ssl_client_cert = config.cert_file,
                        ssl_client_priv_key = config.key_file
                      }
                  )

                  if not res then
                      return kong.response.exit(502, "Introspection failed: " .. (err or "unknown error"))
                  end

                  if res.status ~= 200 then
                      return kong.response.exit(401, "Introspection failed: " .. (res.body or "unknown error"))
                  end

                  kong.service.request.set_header("X-INTROSPECTION", res.body)
                  kong.service.request.set_header("X-INBOUND-TOKEN", kong.request.get_header("Authorization"))

                  res.body = cjson.decode(res.body)
                  if not res.body then
                      return kong.response.exit(502, "Introspection failed: Could not decode response.")
                  end


                  if res.body.jwt == nil then
                      return kong.response.exit(401, "Introspection failed: Expecting jwt in response.")
                  end

                  kong.service.request.set_header("Authorization", "Bearer " .. res.body.jwt)

              - |
                  local jwt_parser = require "kong.plugins.jwt.jwt_parser"
                  local cjson = require "cjson.safe"
                  local crypto = require "resty.openssl"
                  local digest = require "resty.openssl.digest"
                  local utils = require "kong.tools.utils"

                  local assert = assert
                  local rep = string.rep

                  local base64 = require "ngx.base64"

                  local resty_openssl = require "resty.openssl"
                  local pkey = require "resty.openssl.pkey"
                  local bn = require "resty.openssl.bn"
                  local json = require "cjson.safe"
                  local kong = kong

                  local function base64_decode_url(input)
                    local remainder = #input % 4

                    if remainder > 0 then
                      local padlen = 4 - remainder
                      input = input .. rep("=", padlen)
                    end

                    return base64.decode_base64url(input)
                  end

                  local plugin_schema = {
                    type = "record",
                    fields = {
                      {
                        config = {
                          type = "record",
                          fields = {
                            { max_age = { type = "number", default = 60 } },
                            { clock_skew = { type = "number", default = 60 } },
                            { allowed_algorithms = { 
                              type = "array", 
                              elements = { type = "string" },
                              default = { "RS256", "ES256", "PS256" }
                            }},
                            { nonce_cache_ttl = { type = "number", default = 300 } },
                            { anonymous = { type = "string", uuid = true } },
                          }
                        }
                      }
                    }
                  }

                  local config = {
                    max_age = 60,
                    clock_skew = 60,
                    allowed_algorithms = { "RS256", "ES256", "PS256" },
                    nonce_cache_ttl = 300,
                    anonymous = nil,
                  } 

                  local function send_error_response(status, error_code, description)
                    kong.response.set_status(status)
                    kong.response.set_header("Content-Type", "application/json")
                    local body = {
                      error = error_code,
                      error_description = description
                    }
                    return kong.response.exit(status, body)
                  end

                  local function extract_dpop_proof()
                    local dpop_header = kong.request.get_header("DPoP")
                    if not dpop_header then
                      return nil, "DPoP header missing"
                    end
                    return dpop_header, nil
                  end

                  local function extract_access_token()
                    local auth_header = kong.request.get_header("Authorization")
                    if not auth_header then
                      return nil, "Authorization header missing"
                    end
                    local token = auth_header:match("^DPoP%s+(.+)$$") or auth_header:match("^Bearer%s+(.+)$$")
                    if not token then
                      return nil, "Invalid Authorization header format"
                    end
                    return token, nil
                  end

                  local function create_canonical_jwk_json(jwk)
                      local canonical = string.format('{"crv":"%s","kty":"%s","x":"%s","y":"%s"}',
                          jwk.crv, jwk.kty, jwk.x, jwk.y)
                      return canonical
                  end

                  local function calculate_jwk_thumbprint(jwk)
                    if not jwk or type(jwk) ~= "table" then
                      return nil, "Invalid JWK"
                    end
                    
                    local json_str = nil
                    if jwk.kty == "RSA" then
                      canonical_jwk = {
                        e = jwk.e,
                        kty = jwk.kty,
                        n = jwk.n
                      }
                    elseif jwk.kty == "EC" then
                      json_str = create_canonical_jwk_json(jwk)
                    elseif jwk.kty == "OKP" then
                      canonical_jwk = {
                        crv = jwk.crv,
                        kty = jwk.kty,
                        x = jwk.x
                      }
                    else
                      return nil, "Unsupported key type: " .. tostring(jwk.kty)
                    end

                    local hash = digest.new("sha256")
                    hash:update(json_str)
                    local digest_bytes = hash:final()
                    return base64.encode_base64url(digest_bytes), nil
                  end

                  function ec_jwk_to_key(jwk)
                      kong.log.warn("JWK: ", cjson.encode(jwk))
                      local x_bytes = base64_decode_url(jwk.x)
                      local y_bytes = base64_decode_url(jwk.y)
                    
                      
                      local curve_map = {
                          ["P-256"] = "prime256v1",
                          ["P-384"] = "secp384r1",
                          ["P-521"] = "secp521r1"
                      }
                      
                      local curve_name = curve_map[jwk.crv]
                      if not curve_name then
                          return nil, "Unsupported curve: " .. jwk.crv
                      end
                      
                      local key, err = pkey.new(cjson.encode(jwk), {
                          format= "JWK"
                      })
                      if not key then
                          return nil, "Failed to create EC public key: " .. tostring(err)
                      end
                      
                      return key
                  end


                  local function jwk_to_pem(jwk)
                    local pkey = require "resty.openssl.pkey"
                    
                    if jwk.kty == "RSA" then
                      local rsa_params = {
                        n = jwk.n,
                        e = jwk.e
                      }
                      
                      if rsa_params.n then
                        rsa_params.n = base64_decode_url(rsa_params.n)
                      end
                      if rsa_params.e then
                        rsa_params.e = base64_decode_url(rsa_params.e)
                      end
                      
                      local key, err = pkey.new({
                        type = "RSA",
                        bits = nil,
                        rsa_n = rsa_params.n,
                        rsa_e = rsa_params.e
                      })
                      
                      if not key then
                        return nil, "Failed to create RSA public key: " .. tostring(err)
                      end
                      
                      return key, nil
                      
                    elseif jwk.kty == "EC" then
                      local ec_params = {
                        curve = jwk.crv,
                        x = jwk.x,
                        y = jwk.y
                      }
                      
                      if ec_params.x then
                        ec_params.x = base64_decode_url(ec_params.x)
                      end
                      if ec_params.y then
                        ec_params.y = base64_decode_url(ec_params.y)
                      end
                      
                      local curve_name
                      if ec_params.curve == "P-256" then
                        curve_name = "prime256v1"
                      elseif ec_params.curve == "P-384" then
                        curve_name = "secp384r1"  
                      elseif ec_params.curve == "P-521" then
                        curve_name = "secp521r1"
                      else
                        return nil, "Unsupported EC curve: " .. tostring(ec_params.curve)
                      end
                      
                      local key, err = pkey.new({
                        type = "EC",
                        curve = curve_name,
                        ec_x = ec_params.x,
                        ec_y = ec_params.y
                      })
                      
                      if not key then
                        return nil, "Failed to create EC public key: " .. tostring(err)
                      end
                      
                      return key, nil
                      
                    else
                      return nil, "Unsupported key type: " .. tostring(jwk.kty)
                    end
                  end

                  local function extract_public_key_from_header(header)
                    if header.jwk then
                      return ec_jwk_to_key(header.jwk)
                    end
                    if header.x5c and #header.x5c > 0 then
                      return nil, "X.509 certificate processing not implemented"
                    end
                    return nil, "No supported public key format found in header"
                  end

                  local function validate_dpop_proof(dpop_proof, access_token, http_method, http_uri, config)
                    local jwt_parts = utils.split(dpop_proof, ".")
                    if #jwt_parts ~= 3 then
                      return false, "Invalid JWT format"
                    end
                    
                    local header_json = base64_decode_url(jwt_parts[1])
                    if not header_json then
                      return false, "Failed to decode JWT header"
                    end
                    
                    local header = cjson.decode(header_json)
                    if not header then
                      return false, "Failed to parse JWT header JSON"
                    end
                    
                    local payload_json = base64_decode_url(jwt_parts[2])
                    if not payload_json then
                      return false, "Failed to decode JWT payload"
                    end
                    
                    local claims = cjson.decode(payload_json)
                    if not claims then
                      return false, "Failed to parse JWT payload JSON"
                    end
                    
                    if header.typ ~= "dpop+jwt" then
                      return false, "Invalid DPoP JWT type. Expected 'dpop+jwt', got: " .. tostring(header.typ)
                    end
                    
                    local alg_valid = false
                    for _, allowed_alg in ipairs(config.allowed_algorithms) do
                      if header.alg == allowed_alg then
                        alg_valid = true
                        break
                      end
                    end
                    if not alg_valid then
                      return false, "Unsupported algorithm: " .. tostring(header.alg)
                    end
                    
                    local public_key, err = extract_public_key_from_header(header)
                    if not public_key then
                      return false, err or "Failed to extract public key"
                    end
                    
                    local signature = jwt_parts[3]
                    local signature_bytes = base64_decode_url(signature)
                    if not signature_bytes then
                      return false, "Failed to decode JWT signature"
                    end
                    
                    local signing_data = jwt_parts[1] .. "." .. jwt_parts[2]

                    local verified = false
                    if header.alg == "ES256" then
                      assert(#signature_bytes == 64, "Signature must be 64 bytes.")
                      verified, err = public_key:verify(signature_bytes, signing_data, "sha256", nil, { ecdsa_use_raw = true })
                    else
                      return false, "Unsupported signature algorithm: " .. header.alg
                    end
                    
                    if not verified then
                      return false, "DPoP proof signature verification failed"
                    end

                    if not claims.jti then
                      return false, "Missing jti claim"
                    end
                    if not claims.htm or claims.htm ~= http_method then
                      return false, "Invalid htm claim. Expected: " .. http_method .. ", got: " .. tostring(claims.htm)
                    end
                    if not claims.htu then
                      return false, "Missing htu claim"
                    end
                    local expected_htu = http_uri:match("^([^%?#]*)")
                    local provided_htu = claims.htu:match("^([^%?#]*)")
                    if provided_htu ~= expected_htu then
                      return false, "Invalid htu claim. Expected: " .. expected_htu .. ", got: " .. provided_htu
                    end
                    if not claims.iat then
                      return false, "Missing iat claim"
                    end
                    local current_time = ngx.time()
                    local iat = claims.iat
                    if type(iat) ~= "number" then
                      return false, "Invalid iat claim format"
                    end
                    if iat > current_time + config.clock_skew then
                      return false, "DPoP proof issued in the future"
                    end
                    if current_time - iat > config.max_age then
                      return false, "DPoP proof too old"
                    end
                    local cache_key = "dpop_jti:" .. claims.jti
                    local cached_jti = kong.cache:get(cache_key)
                    if cached_jti then
                      return false, "DPoP proof replay detected"
                    end

                    return true, nil, {
                      public_key = public_key,
                      jwk = header.jwk,
                      jti = claims.jti,
                      iat = claims.iat,
                      claims = claims
                    }
                  end

                  local function validate_token_binding(access_token, dpop_public_key)
                    local token_jwt, err = jwt_parser:new(access_token)
                    if err then
                      return false, "Invalid access token format: " .. err
                    end
                    local claims = token_jwt.claims
                    if not claims.cnf or not claims.cnf.jkt then
                      return false, "Access token not bound to DPoP key (missing cnf.jkt claim)"
                    end
                    local dpop_thumbprint, err = calculate_jwk_thumbprint(dpop_public_key)
                    if not dpop_thumbprint then
                      return false, "Failed to calculate DPoP key thumbprint: " .. tostring(err)
                    end

                    if claims.cnf.jkt ~= dpop_thumbprint then
                      return false, "DPoP key thumbprint mismatch"
                    end
                    return true, nil, {
                      token_claims = claims,
                      dpop_thumbprint = dpop_thumbprint
                    }
                  end

                  local method = kong.request.get_method()
                  local scheme = kong.request.get_scheme()
                  local host = kong.request.get_host()
                  local port = kong.request.get_port()
                  local path = kong.request.get_path()
                  local uri = scheme .. "://" .. host
                  uri = uri .. path

                  local dpop_proof, err = extract_dpop_proof()
                  if not dpop_proof then
                    if config.anonymous then
                      kong.client.authenticate(nil, config.anonymous)
                      return
                    end
                    return send_error_response(401, "invalid_request", err)
                  end

                  local access_token, err = extract_access_token()
                  if not access_token then
                    return send_error_response(401, "invalid_request", err)
                  end

                  local valid, err, dpop_data = validate_dpop_proof(dpop_proof, access_token, method, uri, config)
                  if not valid then
                    return send_error_response(401, "invalid_dpop_proof", err)
                  end

                  local bound, err, binding_data = validate_token_binding(access_token, dpop_data.jwk)
                  if not bound then
                    return send_error_response(401, "invalid_token", err)
                  end

                  kong.ctx.shared.dpop_validated = true
                  kong.ctx.shared.access_token = access_token
                  kong.ctx.shared.dpop_public_key = dpop_data.public_key
                  kong.ctx.shared.dpop_claims = dpop_data.claims
                  kong.ctx.shared.token_claims = binding_data.token_claims
                  kong.ctx.shared.dpop_jti = dpop_data.jti

                  local subject = binding_data.token_claims.sub
                  if subject then
                    kong.client.authenticate({ id = subject }, nil)
                  end

                  kong.log.info("DPoP validation successful for JTI: ", dpop_data.jti)

                  kong.service.request.set_header("X-DPoP-Validated", "true" )



      - name: ${service_name}.SIGNED
        tags: [ns.${gateway}.${ns_qualifier}, sdx]
        hosts:
          - ${route_host}
        paths:
          - ${route_path}
        headers:
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

def eval_service_pattern (context):
  return template.substitute(context)
