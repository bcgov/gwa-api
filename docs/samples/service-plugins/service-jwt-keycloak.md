services:
- name: MY_REST_API
  tags: [ _NS_ ]
  plugins:
  - name: jwt-keycloak
    tags: [ _NS_ ]
    enabled: true
    config:
      client_roles: null
      allowed_iss:
      - https://authz-264e6f-dev.apps.silver.devops.gov.bc.ca/auth/realms/aps
      run_on_preflight: true
      iss_key_grace_period: 10
      maximum_expiration: 0
      claims_to_verify:
      - exp
      consumer_match_claim_custom_id: false
      cookie_names: []
      scope: null
      uri_param_names
      - jwt
      roles: null
      consumer_match: false
      well_known_template: https://authz-264e6f-dev.apps.silver.devops.gov.bc.ca/auth/realms/aps/.well-known/openid-configuration
      consumer_match_ignore_not_found: false
      anonymous: null
      algorithm: RS256
      realm_roles: null
      consumer_match_claim: azp
  }
}
