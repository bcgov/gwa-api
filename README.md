# Gateway Administration (GWA) Microservice APIs

[![Lifecycle:Stable](https://img.shields.io/badge/Lifecycle-Stable-97ca00?style=for-the-badge)](https://github.com/bcgov/repomountie/blob/master/doc/lifecycle-badges.md)
[![GitHub Workflow Status (branch)](https://img.shields.io/github/actions/workflow/status/bcgov/gwa-api/master.yml?branch=master&style=for-the-badge)](https://github.com/bcgov/api-services-portal/actions/workflows/ci-build-deploy.yaml)
[![Coverage](https://img.shields.io/sonar/coverage/gwa-api/dev?server=https%3A%2F%2Fsonarcloud.io&style=for-the-badge)](https://sonarcloud.io/summary/new_code?id=gwa-api&branch=feature%2Froute-template-override)
![GitHub](https://img.shields.io/github/license/bcgov/gwa-api?style=for-the-badge)
![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/bcgov/gwa-api?label=release&style=for-the-badge)

For self-service of APIs, a set of microservices are used to coordinate updates by the providers of APIs.

- `Gateway` : Provides a way for API Owners to update their Kong configuration (and internally the OCP Edge Router)
- `Authz` : Provides a way for API Owners to update Keycloak for access to functionality on the API Services Portal
- `Catalog` : Provides a way for API Owners to update the API details in the BC Data Catalog

All APIs are protected by an OIDC JWT Token with the following claims:

- `aud` : `gwa`
- `namespace` : Identifies the namespace that the APIs belong to, used to scope what changes are allowed

**Configuration:**

| Variable                              | Description                                                                                                                                                | Example                                   |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| `PORT`                                | Port                                                                                                                                                       | `2000`                                    |
| `LOG_LEVEL`                           | Log level for the application                                                                                                                              | `INFO`                                    |
| `ENVIRONMENT`                         | Indicates what environment config to use (development , test, production)                                                                                  | `production`                              |
| `CONFIG_PATH`                         | Location of the config                                                                                                                                     | `/tmp/production.json`                    |
| `OIDC_BASE_URL`                       | External base url used by the Swagger console for an externally available Auth endpoint.                                                                   | `https://keycloak.domain/auth/realms/abc` |
| `TOKEN_MATCH_AUD`                     | The `audience` that the token must match.                                                                                                                  | `gwa`                                     |
| `WORKING_FOLDER`                      | Temporary working folder that only exists for the duration of the POD.                                                                                     | `/tmp`                                    |
| `KONG_ADMIN_URL`                      | The Kong Admin endpoint.                                                                                                                                   | `http://kong-admin-api:8001`              |
| `KC_SERVER_URL`                       | Keycloak access for administrative rights to manage groups for namespaces and for OIDC Discovery for getting the `jwks_uri` for the list of supported keys | `https://auth.domain/auth`                |
| `KC_REALM`                            | Keycloak access for administrative rights to manage groups for namespaces                                                                                  | `aps`                                     |
| `KC_CLIENT_ID`                        | Keycloak access for administrative rights to manage groups for namespaces                                                                                  | `admin-cli`                               |
| `KC_CLIENT_SECRET`                    | Keycloak access for administrative rights to manage groups for namespaces                                                                                  | ``                                        |
| `KC_USER_REALM`                       | Keycloak access for administrative rights to manage groups for namespaces                                                                                  | `master`                                  |
| `KC_USERNAME`                         | Keycloak access for administrative rights to manage groups for namespaces                                                                                  | `kcadmin`                                 |
| `KC_PASSWORD`                         | Keycloak access for administrative rights to manage groups for namespaces                                                                                  | `xxx`                                     |
| `HOST_TRANSFORM_ENABLED`              | For Dev and Test a way to transform the host for working in these environments                                                                             | `false`                                   |
| `HOST_TRANSFORM_BASE_URL`             | For Dev and Test a way to transform the host for working in these environments                                                                             |
| `PLUGINS_RATELIMITING_REDIS_PASSWORD` | The Redis credential added to the rate-limiting Kong plugin during publish                                                                                 |

# API Provider Flow

[See Details](https://bcgov.github.io/aps-infra-platform/guides/owner-journey)
