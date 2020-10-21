# GWA APIs

For self-service of the APIs, a set of microservices are used to coordinate updates by the API Owners.

* Gateway API : Provides a way for API Owners to update their Kong configuration (and internally the OCP Edge Router)
* Authz API : Provides a way for API Owners to update Keycloak for access to the API Services Portal
* Catalog API : Providers a way for API Owners to update the API details in the BC Data Catalog

All APIs are protected by an OIDC JWT Token with the following claims:

* `aud` : https://gwa-qwzrwc-dev.pathfinder.gov.bc.ca/
* `namespace` : Identifies the namespace that the APIs belong to, used to scope what changes are synced with Kong
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
| `KC_SERVER_URL`   | Keycloak access for administrative rights to manage groups for namespaces | `https://auth.domain/auth`
| `KC_REALM`        | Keycloak access for administrative rights to manage groups for namespaces | `aps`
| `KC_CLIENT_ID`    | Keycloak access for administrative rights to manage groups for namespaces | `admin-cli`
| `KC_CLIENT_SECRET`| Keycloak access for administrative rights to manage groups for namespaces | ``
| `KC_USER_REALM`   | Keycloak access for administrative rights to manage groups for namespaces | `master`
| `KC_USERNAME`     | Keycloak access for administrative rights to manage groups for namespaces | `kcadmin`
| `KC_PASSWORD`     | Keycloak access for administrative rights to manage groups for namespaces | `xxx`

## Gateway API

The `Gateway API` has a `dry-run` and `sync` of Kong and OCP configuration.

The token must have a valid scope for managing the config.


# Access

```
scope := permission/resource.access

permission, resource, access := any string (without space, period, slash, or asterisk) | asterisk
```

permission type is based on single or bulk records.

resource types: GatewayConfig, Catalog

access: read, write

# Flow

## 1. Register a new namespace

A `namespace` represents a collections of Kong Services and Routes that are managed independently.

To create a new namespace, go to the <a href="https://gwa-qwzrwc-test.pathfinder.gov.bc.ca/int" target="_blank">API Services Portal</a>.

After login and selection of an existing namespace, go to the `New Namespace` tab and click the `Create Namespace` button.

The namespace must be an alphanumeric string between 5 and 10 characters.

Logout by clicking your username at the top right of the page.  When you login again, you should be able to select the new namespace from the `API Programme Services` project selector.

## 2. Generate a Service Account

Go to the `Service Accounts` tab and click the `Create Service Account`.  A new credential will be created - make a note of the `ID` and `Secret`.

With scopes:
* `admin:gateway` : Permission to publish gateway configuration to Kong
* `admin:acl`     : Permission to update the Access Control List for controlling access to viewing metrics, service configuration and service account management
* `admin:catalog` : Permission to update BC Data Catalog datasets for describing APIs available for consumption

## 3. Prepare configuration

The gateway configuration can be hand-crafted or you can use the `gwa` `new` command to walk you through the creation of the config.

You can view examples [here](/docs/samples/service-plugins).

**Simple Example**

```
export NS="my_namespace"
export NAME="a-service-for-$NS"
echo "
services:
- name: $NAME
  host: httpbin.org
  tags: [ ns.$NS ]
  port: 443
  protocol: https
  retries: 0
  routes:
  - name: $NAME-route
    tags: [ ns.$NS ]
    hosts:
    - $NAME.api.189768.xyz
    paths:
    - /
    strip_path: false
    https_redirect_status_code: 426
    path_handling: v0
" > sample.yaml
```

**gwa CLI Example**

Run: `gwa new` and follow the prompts.

## 4. Apply gateway configuration

The Swagger console for the `gwa-api` can be used to publish Kong Gateway configuration, or the `gwa-cli` can be used.

### Swagger Console

Go to <a href="https://gwa-api-qwzrwc-test.pathfinder.gov.bc.ca/api/doc" target="_blank">gwa-api Swagger Console</a>.

Select the `PUT` `/namespaces/{namespace}/gateway` API.

The Service Account uses the OAuth2 Client Credentials Grant Flow.  Click the `lock` link on the right and enter in the Service Account credentials that were generated in step #2.

For the `Parameter namespace`, enter the namespace that you created in step #1.

Select `dryRun` to `true`.

Select a `configFile` file.

Send the request.

### Command Line

**Install**

```
git clone -b feature/feature-refactor https://github.com/bcgov/gwa-cli.git
cd gwa-cli
npm install
npm run build
npm link
```

**Configure**

Create a `.env` file and update the CLIENT_ID and CLIENT_SECRET with the new credentials that were generated in step #2:

```
echo "
GWA_NAMESPACE=$NS
CLIENT_ID=<YOUR SERVICE ACCOUNT ID>
CLIENT_SECRET=<YOUR SERVICE ACCOUNT SECRET>
GWA_ENV=test
" > .env

OR run:

gwa init -T --namespace=$NS --client-id=<YOUR SERVICE ACCOUNT ID> --client-secret=<YOUR SERVICE ACCOUNT SECRET>

```

**Publish**

```
gwa pg sample.yaml 
```

## 5. Verify routes

```
curl https://$NAME.api.189768.xyz/headers

ab -n 20 -c 2 https://$NAME.api.189768.xyz/headers

```

## 6. View metrics

Go to <a href="https://grafana-qwzrwc-test.pathfinder.gov.bc.ca/" target="_blank">Grafana</a> to view metrics for your configured services.


## 7. Grant access to others

The `acl` command is an all-inclusive membership list, so the `--users` should have the full list of members.  Any user that is a member but not in the `--users` list will be removed from the namespace.

```
gwa acl --users acope@idir jjones@idir
```

## 8. Add to your CI/CD Pipeline

Update your CI/CD pipelines to run the `gwa-cli` to keep your services updated on the gateway.

> TODO: Examples
