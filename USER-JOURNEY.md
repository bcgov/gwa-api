# API Owner Flow

The following steps walk an API Owner through setting up an API on the BC Gov API Gateway in our Test instance.  If you are ready to deploy to our Production instance, use the links [here](#production-links).

## Prerequisites

If you have not requested access to the API Gateway Services, then you must first go to the [API Services Portal](https://api-gov-bc-ca.test.api.gov.bc.ca), and:

* login using your IDIR or Github account
* go to the `Directory` tab and select the "API Gateway Services"
* on the "API Gateway Services" detail page, there will be a button in the top right "Request Access"
* select your Application (you need to create one if you have not already)
* select the "test" environment and click "Submit"

You will be provided with credentials for accessing the Gateway Services API, but you will need to wait until the request has been approved for the credential to be active and authorized.


## 1. Register a new namespace

A `namespace` represents a collection of Kong Services and Routes that are managed independently.

To create a new namespace, go to the [API Services Portal](https://api-gov-bc-ca.test.api.gov.bc.ca).

After login, click the namespace dropdown in the top right next to your user name, then click `Create New Namespace`.

The namespace must be an alphanumeric string between 5 and 15 characters (RegExp reference: `^[a-z][a-z0-9-]{4,14}$`).

You can select and manage namespaces by clicking the namespace dropdown in the top right next to your user name.

## 2. Generate a Service Account

Go to the `Namespaces` tab, click the `Service Accounts` link, and click the `New Service Account`.  A new credential will be created - make a note of the `ID` and `Secret`.

Before the credential can be used, you need to grant it the appropriate Scopes.  This can be done by going to the `API Access` tab and click the "Manage Resources" for the `Gateway Administration API` product.  Click the link that corresponds to your newly created namespace.  Click the `Grant Service Account Access` and enter in the `ID` and the scopes you want to grant to the Service Account, then click the `Share` button to grant the permissions.

The available Scopes are:
| Scope | Permission |
| ----- | ---------- |
| `Namespace.Manage`  | Permission to update the Access Control List for controlling access to viewing metrics, service configuration and service account management (effectively a superuser for the namespace) |
| `Namespace.View`   | Read-only access to the namespace |
| `GatewayConfig.Publish` | Permission to publish gateway configuration to Kong and to view the status of the upstreams |
| `Content.Publish`  | Permission to update the documentation on the portal |
| `CredentialIssuer.Admin`    | Permission to create Authorization Profiles so that they are available to be used when configuring Product Environments |
| `Access.Manage`    | Permission to approve/reject access requests to your APIs that you make discoverable |

## 3. Prepare configuration

The gateway configuration can be hand-crafted or you can use a command line interface that we developed called `gwa` to convert your Openapi v3 spec to a Kong configuration.

### 3.1. Hand-crafted (recommended if you don't have an Openapi spec)

**Simple Example**

``` bash
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
    - $NAME.api.gov.bc.ca
    paths:
    - /
    methods:
    - GET
    strip_path: false
    https_redirect_status_code: 426
    path_handling: v0
" > sample.yaml
```

> To view common plugin config go to [COMMON-CONFIG.md](/docs/COMMON-CONFIG.md)

> To view some other plugin examples go [here](/docs/samples/service-plugins).

> **Declarative Config** Behind the scenes, DecK is used to sync your configuration with Kong.  For reference: https://docs.konghq.com/deck/overview/

> **Splitting Your Config:** A namespace `tag` with the format `ns.$NS` is mandatory for each service/route/plugin.  But if you have separate pipelines for your environments (i.e./ dev, test and prod), you can split your configuration and update the `tags` with the qualifier.  So for example, you can use a tag `ns.$NS.dev` to sync Kong configuration for `dev` Service and Routes only.

> **Upstream Services on OCP4:** If your service is running on OCP4, you should specify the Kubernetes Service in the `Service.host`.  It must have the format: `<name>.<ocp-namespace>.svc`.  Also make sure your `Service.port` matches your Kubernetes Service Port.  Any Security Policies for egress from the Gateway will be setup automatically on the API Gateway side.
> The Aporeto Network Security Policies are being removed in favor of the Kubernetes Security Policies (KSP).  You will need to create a KSP on your side looking something like this to allow the Gateway's test and prod environments to route traffic to your API:

``` yaml
kind: NetworkPolicy
apiVersion: networking.k8s.io/v1
metadata:
  name: allow-traffic-from-gateway-to-your-api
spec:
  podSelector:
    matchLabels:
      name: my-upstream-api
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              environment: test
              name: 264e6f
    - from:
        - namespaceSelector:
            matchLabels:
              environment: prod
              name: 264e6f
```

> **Migrating from OCP3 to OCP4?** Please review the [OCP4-Migration](docs/OCP4-MIGRATION.md) instructions to help with transitioning to OCP4 and the new APS Gateway.

> **Require mTLS between the Gateway and your Upstream Service?** To support mTLS on your Upstream Service, you will need to provide client certificate details and if you want to verify the upstream endpoint then the `ca_certificates` and `tls_verify` is required as well.  An example:

``` yaml
services:
- name: my-upstream-service
  host: my-upstream.site
  tags: [ _NS_ ]
  port: 443
  protocol: https
  tls_verify: true
  ca_certificates: [ 0a780ee0-626c-11eb-ae93-0242ac130012 ]
  client_certificate: 8fc131ef-9752-43a4-ba70-eb10ba442d4e
  routes: [ ... ]
certificates:
- cert: "<PEM FORMAT>"
  key: "<PEM FORMAT>"
  tags: [ _NS_ ]
  id: 8fc131ef-9752-43a4-ba70-eb10ba442d4e
ca_certificates:
- cert: "<PEM FORMAT>"
  tags: [ _NS_ ]
  id: 0a780ee0-626c-11eb-ae93-0242ac130012
```

> NOTE: You must generate a UUID (`python -c 'import uuid; print(uuid.uuid4())'`) for each certificate and ca_certificate you create (set the `id`) and reference it in your `services` details.

> HELPER: Python command to get a PEM file on one line: `python -c 'import sys; import json; print(json.dumps(open(sys.argv[1]).read()))' my.pem`

### 3.2. gwa Command Line

Run: `gwa new` and follow the prompts.

Example:

``` bash
gwa new -o sample.yaml \
  --route-host myapi.api.gov.bc.ca \
  --service-url https://httpbin.org \
  https://bcgov.github.io/gwa-api/openapi/simple.yaml
```

> See below for the `gwa` CLI install instructions.

## 4. Apply gateway configuration

The Swagger console for the `gwa-api` can be used to publish Kong Gateway configuration, or the `gwa Command Line` can be used.

### 4.1. gwa Command Line (recommended)

**Install (for Linux)**

``` bash
GWA_CLI_VERSION=v1.2.0; curl -L -O https://github.com/bcgov/gwa-cli/releases/download/${GWA_CLI_VERSION}/gwa_${GWA_CLI_VERSION}_linux_x64.zip
unzip gwa_${GWA_CLI_VERSION}_linux_x64.zip
./gwa --version
```

> **Using MacOS or Windows?** Download here: [https://github.com/bcgov/gwa-cli/releases/tag/v1.2.0](https://github.com/bcgov/gwa-cli/releases/tag/v1.2.0)

**Configure**

Create a `.env` file and update the CLIENT_ID and CLIENT_SECRET with the new credentials that were generated in step #2:

``` bash
echo "
GWA_NAMESPACE=$NS
CLIENT_ID=<YOUR SERVICE ACCOUNT ID>
CLIENT_SECRET=<YOUR SERVICE ACCOUNT SECRET>
GWA_ENV=test
API_VERSION=2
" > .env

OR run:

gwa init -T --namespace=$NS --client-id=<YOUR SERVICE ACCOUNT ID> --client-secret=<YOUR SERVICE ACCOUNT SECRET>

```

> NOTE: The `-T` indicates our Test environment.  For production use `-P`.

**Publish**

``` bash
gwa pg sample.yaml 
```

If you want to see the expected changes but not actually apply them, you can run:

``` bash
gwa pg --dry-run sample.yaml
```

### 4.2. Swagger Console

Go to [gwa-api Swagger Console](https://gwa-api-gov-bc-ca.test.api.gov.bc.ca/docs).

Select the `PUT` `/namespaces/{namespace}/gateway` API.

The Service Account uses the OAuth2 Client Credentials Grant Flow.  Click the `lock` link on the right and enter in the Service Account credentials that were generated in step #2.

For the `Parameter namespace`, enter the namespace that you created in step #1.

Select `dryRun` to `true`.

Select a `configFile` file.

Send the request.

### 4.3. Postman

From the Postman App, click the `Import` button and go to the `Link` tab.

Enter a URL: https://openapi-to-postman-api-gov-bc-ca.test.api.gov.bc.ca/?u=https://gwa-api-gov-bc-ca.test.api.gov.bc.ca/doc/v2/swagger.json

After creation, go to `Collections` and right-click on the `Gateway Administration (GWA) API` collection and select `edit`.

Go to the `Authorization` tab, enter in your `Client ID` and `Client Secret` and click `Get New Access Token`.

You should get a successful dialog to proceed.  Click `Proceed` and `Use Token`.

You can then verify that the token works by going to the Collection `Return key information about authenticated identity` and click `Send`.

## 5. Verify routes

To verify that the Gateway can access the upstream services, run the command: `gwa status`.

In our test environment, the hosts that you defined in the routes get altered; to see the actual hosts, log into the [API Services Portal](https://api-gov-bc-ca.test.api.gov.bc.ca), go to the `Namespaces` tab, go to `Gateway Services` and select your particular service to get the routing details.

``` bash
curl https://${NAME}-api-gov-bc-ca.test.api.gov.bc.ca/headers

ab -n 20 -c 2 https://${NAME}-api-gov-bc-ca.test.api.gov.bc.ca/headers

```

To help with troubleshooting, you can use the GWA API to get a health check for each of the upstream services to verify the Gateway is connecting OK.

Go to the [GWA API](https://gwa-api-gov-bc-ca.test.api.gov.bc.ca/docs#/Service%20Status/get_namespaces__namespace__services), enter in the new credentials that were generated in step #2, click `Try it out`, enter your namespace and click `Execute`.  The results are returned in a JSON object.

## 6. View metrics

The following metrics can be viewed in real-time for the Services that you configure on the Gateway:

* Request Rate : Requests / Second (by Service/Route, by HTTP Status)
* Latency : Standard deviations measured for latency inside Kong and on the Upstream Service (by Service/Route)
* Bandwidth : Ingress/egress bandwidth (by Service/Route)
* Total Requests : In 5 minute windows (by Consumer, by User Agent, by Service, by HTTP Status)

All metrics can be viewed by an arbitrary time window - defaults to `Last 24 Hours`.

Go to [Grafana](https://grafana-apps-gov-bc-ca.test.api.gov.bc.ca) to view metrics for your configured services.

You can also access summarized metrics from the `API Services Portal` by going to the `Namespaces` tab and clicking the `Gateway Services` link.

## 7. Grant access to others

To grant access to others, you need to grant them the appropriate Scopes.  This can be done from the `API Services Portal`, going to the `API Access` tab and clicking the "Manage Resources" for the `Gateway Administration API` product.  Click the link that corresponds to your namespace.  Click the `Grant User Access` and enter in a username (i.e./ `jsmith@idir`) and the scopes you want to grant to the User, then click the `Share` button to grant the permissions.

## 8. Add to your CI/CD Pipeline

Update your CI/CD pipelines to run the `gwa-cli` to keep your services updated on the gateway.

### 8.1. Github Actions Example

In the repository that you maintain your CI/CD Pipeline configuration, use the Service Account details from `Step 2` to set up two `Secrets`:

* GWA_ACCT_ID

* GWA_ACCT_SECRET

Add a `.gwa` folder (can be called anything) that will be used to hold your gateway configuration.

An example Github Workflow:

``` yaml
env:
  NS: "<your namespace>"
  
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
      with:
        fetch-depth: 0
        
    - uses: actions/setup-node@v1
      with:
        node-version: 10
        TOKEN: ${{ secrets.GITHUB_TOKEN }}

    - name: Get GWA Command Line
      run: |
        curl -L -O https://github.com/bcgov/gwa-cli/releases/download/v1.2.0/gwa_v1.2.0_linux_x64.zip
        unzip gwa_v1.2.0_linux_x64.zip
        export PATH=`pwd`:$PATH

    - name: Apply Namespace Configuration
      run: |
        export PATH=`pwd`:$PATH
        cd .gwa/$NS

        gwa init -T \
          --namespace=$NS \
          --client-id=${{ secrets.TEST_GWA_ACCT_ID }} \
          --client-secret=${{ secrets.TEST_GWA_ACCT_SECRET }}

        gwa pg

        gwa acl --managers acope@idir
       
```

## 9. Share your API for Discovery

Package your APIs and make them available for discovery through the API Services Portal and BC Data Catalog.

The `API Services Portal` Directory organizes your APIs by Products and Environments.  You can manage them via an API or through the UI.

To use the Directory API, the following scopes are required:

* For `contents` (documentation), the service account must have the `Content.Publish` scope
* For `datasets` and `products`, the service account must have the `Namespace.Manage` scope
* For `issuers`, the service account must have the `CredentialIssuer.Admin` scope

View the Directory API in the [Swagger Console](https://openapi-apps-gov-bc-ca.test.api.gov.bc.ca/?url=https://api-gov-bc-ca.test.api.gov.bc.ca/ds/api/openapi.yaml)

> NOTE: The steps below use `restish`, but we will be working on upgrading the `gwa` command line interface to support these APIs

> Can use `y2j` to convert from YAML to JSON
>
> `echo '#!/usr/bin/env python\nimport sys,yaml,json\nprint(json.dumps(yaml.safe_load(open(sys.argv[1]).read())))' > /usr/local/bin/y2j`
>
> chmod +x /usr/local/bin/y2j

**Restish Setup**

```
restish api configure my_api
```

Base URI : https://api-gov-bc-ca.test.api.gov.bc.ca/ds/api

Select `Setup Auth` > `oauth-client-credentials`

Enter the `client_id` and `client_secret` for your Service Account.

`token_url` : Provided to you when you created the Service Account

`scopes` : openid

Select `Finished with Profile` and then `Save and exit`

To verify that restish is working, run:

`restish my_api list` or `restish my_api get-new-id product`

You may need to get the `openapi.yaml` manually, and edit `~/.restish/apis.json` with:

curl -O https://api-gov-bc-ca.test.api.gov.bc.ca/ds/api/openapi.yaml

```
    "spec_files": [
      "openapi.yaml"
    ],
```


### 9.1 Setup Authorization Profiles

Example configuration:

``` yaml
kind: CredentialIssuer
name: Resource Server $NS
namespace: $NS
description: Authorization Profile for protecting Ministry of Health Services
flow: client-credentials
mode: auto
authPlugin: jwt-keycloak
clientAuthenticator: client-secret
clientRoles: []
availableScopes: [System/Patient.*, System/MedicationRequest.*]
owner: acope@idir
environmentDetails:
  - environment: prod
    issuerUrl: https://dev.oidc.gov.bc.ca/auth/realms/xtmke7ky
    clientId: abc-client
    clientRegistration: managed
    clientSecret: ''
```

```
y2j issuer.yaml | restish my_api put-issuer $NS
```

### 9.2 Publish your Product, Environments and link your Services

Example configuration:

``` yaml  
kind: DraftDataset
name: $NS-draft
organization: ministry-of-health
organizationUnit: planning-and-innovation-division
title: $NS API
notes: Some information about this API
tags: [health, standards, openapi]
sector: Service
license_title: Access Only
view_audience: Government
security_class: LOW-PUBLIC
record_publish_date: '2021-05-27'
```

```
y2j dataset.yaml | restish my_api put-dataset $NS
```

```
kind: Product
appId: 2B04C28E08AW
name: My $NS API
dataset: $NS-draft
environments:
- id: 1F7CA929
  name: prod
  active: true
  approval: true
  flow: client-credentials
  credentialIssuer: Resource Server $NS
  additionalDetailsToRequest: Please provider a bit more of this
  services: []
```

```
y2j prod.yaml | restish my_api put-product $NS
```

### 9.3 Publish Documentation

``` yaml
title: Getting Started with $NS
description: Getting Started with $NS
externalLink: https://github.com/bcgov/$NS/getting_started.md
order: 1
tags: [ ns.$NS ]
isComplete: true
isPublic: true
publishDate: '2021-05-22T12:00:00.000-08:00'
```

```
y2j content.yaml | restish my_api put-content $NS 

echo "# here is some markdown!" > doc.md

restish my_api put-content $NS \
  externalLink: "https://github.com/bcgov/$NS/getting_started.md", \
  content: @doc.md
```

### 9.4 View your product in the API Directory

Find your API in the [API Services Portal Directory](https://api-gov-bc-ca.test.api.gov.bc.ca/devportal/api-discovery)

It is now ready to receive access requests from the community.

# Production Links

* [API Services Portal](https://api.gov.bc.ca)
* [gwa-api Swagger Console](https://gwa.api.gov.bc.ca/docs)
* OpenAPI to Postman Converter: https://openapi-to-postman.api.gov.bc.ca/?u=https://gwa.api.gov.bc.ca/api/doc/swagger.json
* [APS Metrics - Grafana](https://grafana.apps.gov.bc.ca)
