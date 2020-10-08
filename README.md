# GWA APIs

For self-service of the APIs, a set of microservices are used to coordinate updates by the API Owners.

* Gateway API : Provides a way for API Owners to update their Kong configuration (and internally the OCP Edge Router)
* Authz API : Provides a way for API Owners to update Keycloak for access to the API Services Portal
* Catalog API : Providers a way for API Owners to update the API details in the BC Data Catalog

All APIs are protected by an OIDC JWT Token with the following claims:

* `aud` : https://gwa-qwzrwc-dev.pathfinder.gov.bc.ca/
* `team` : Identifies the team that the APIs belong to, used to scope what changes are synced with Kong
* `scope` : `manage:config`

**Configuration:**

| Variable          | Description | Example |
| --------          | ----------- | ------- |
| `PORT`            | Port        | `2000` |
| `LOG_LEVEL`       | Log level for the application | `INFO` |
| `ENVIRONMENT`     | Indicates what environment config to use | `production` |
| `CONFIG_PATH`     | Location of the config | `/tmp/production.json` |
| `OIDC_BASE_URL`   | Base url used for OIDC Discovery for getting the `jwks_uri` for the list of supported keys. | `https://keycloak.domain/auth/realms/abc`
| `TOKEN_MATCH_AUD` | The `audience` that the token must match. | `gwa`
| `WORKING_FOLDER`  | Temporary working folder that only exists for the duration of the POD. | `/tmp`
| `KONG_ADMIN_URL`  | The Kong Admin endpoint. | `http://kong-admin-api:8001`

## Gateway API

The `Gateway API` has a `dry-run` and `sync` of Kong and OCP configuration.

The token must have a valid scope for managing the config.
