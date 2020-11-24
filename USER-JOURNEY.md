# API Provider Flow

## 1. Register a new namespace

A `namespace` represents a collection of Kong Services and Routes that are managed independently.

To create a new namespace, go to the <a href="https://gwa-264e6f-test.apps.silver.devops.gov.bc.ca/int" target="_blank">API Services Portal</a>.

After login (and selection of an existing namespace if you have one already assigned), go to the `New Namespace` tab and click the `Create Namespace` button.

The namespace must be an alphanumeric string between 5 and 15 characters (RegExp reference: `^[a-z][a-z0-9-]{4,14}$`).

Logout by clicking your username at the top right of the page.  When you login again, you should be able to select the new namespace from the `API Programme Services` project selector.

## 2. Generate a Service Account

Go to the `Service Accounts` tab and click the `Create Service Account`.  A new credential will be created - make a note of the `ID` and `Secret`.

The credential has the following access:
* `admin:gateway` : Permission to publish gateway configuration to Kong
* `admin:acl`     : Permission to update the Access Control List for controlling access to viewing metrics, service configuration and service account management
* `admin:catalog` : Permission to update BC Data Catalog datasets for describing APIs available for consumption

## 3. Prepare configuration

The gateway configuration can be hand-crafted or you can use a command line interface that we developed called `gwa` to convert your Openapi v3 spec to a Kong configuration.

### Hand-crafted (recommended if you don't have an Openapi spec)

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
    - $NAME.api.gov.bc.ca
    paths:
    - /
    strip_path: false
    https_redirect_status_code: 426
    path_handling: v0
" > sample.yaml
```

To view optional plugin examples go [here](/docs/samples/service-plugins).

> **Splitting Your Config:** A namespace `tag` with the format `ns.$NS` is mandatory for each service/route/plugin.  But if you have separate pipelines for your environments (i.e./ dev, test and prod), you can split your configuration and update the `tags` with the qualifier.  So for example, you can use a tag `ns.$NS.dev` to sync Kong configuration for `dev` Service and Routes only.

> **Upstream Services on OCP4:** If your service is running on OCP4, you should specify the Kubernetes Service in the `Service.host`.  It must have the format: `<name>.<ocp-namespace>.svc` The Network Security Policies (NSP) will be setup automatically on the API Gateway side.  You will need to create an NSP on your side looking something like this to allow the Gateway's test and prod environments to route traffic to your API:

```
kind: NetworkSecurityPolicy
apiVersion: security.devops.gov.bc.ca/v1alpha1
metadata:
  name: aps-gateway-to-your-upstream-api
spec:
  description: |
    allow aps gateway to route traffic to your api
  source:
    - - $namespace=264e6f-test
      - app.kubernetes.io/name=kong
    - - $namespace=264e6f-prod
      - app.kubernetes.io/name=kong
  destination:
    - - app.kubernetes.io/name=my-upstream-api
```


### gwa Command Line

Run: `gwa new` and follow the prompts.

Example:

```
gwa new -o sample.yaml \
  --route-host myapi.api.gov.bc.ca \
  --service-url https://httpbin.org \
  https://bcgov.github.io/gwa-api/openapi/simple.yaml
```

> See below for the `gwa` CLI install instructions.

## 4. Apply gateway configuration

The Swagger console for the `gwa-api` can be used to publish Kong Gateway configuration, or the `gwa Command Line` can be used.

### gwa Command Line (recommended)

**Install (for Linux) **

```
curl -L -O https://bcgov.github.io/gwa-cli/gwa_v1.0.10_linux_x64.zip
unzip gwa_v1.0.10_linux_x64.zip
./gwa --version
```

> MacOS or Windows? For Mac `gwa_v1.0.10_macos_x64.zip` and for Windows `gwa_v1.0.10_win_x64.zip`

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

If you want to see the expected changes but not actually apply them, you can run:

```
gwa pg --dry-run sample.yaml
```

### Swagger Console

Go to <a href="https://gwa-api-264e6f-test.apps.silver.devops.gov.bc.ca/api/doc" target="_blank">gwa-api Swagger Console</a>.

Select the `PUT` `/namespaces/{namespace}/gateway` API.

The Service Account uses the OAuth2 Client Credentials Grant Flow.  Click the `lock` link on the right and enter in the Service Account credentials that were generated in step #2.

For the `Parameter namespace`, enter the namespace that you created in step #1.

Select `dryRun` to `true`.

Select a `configFile` file.

Send the request.


## 5. Verify routes

In our test environment, the hosts that you defined in the routes get altered; to see the actual hosts, log into the <a href="https://gwa-264e6f-test.apps.silver.devops.gov.bc.ca//int" target="_blank">API Services Portal</a> and view the hosts under `Services`.

```
curl https://${NAME}-api-gov-bc-ca.test.apsgw.xyz/headers

ab -n 20 -c 2 https://${NAME}-api-gov-bc-ca.test.apsgw.xyz/headers

```

## 6. View metrics

The following metrics can be viewed in real-time for the Services that you configure on the Gateway:

* Request Rate : Requests / Second (by Service/Route, by HTTP Status)
* Latency : Standard deviations measured for latency inside Kong and on the Upstream Service (by Service/Route)
* Bandwidth : Ingress/egress bandwidth (by Service/Route)
* Total Requests : In 5 minute windows (by Consumer, by User Agent, by Service, by HTTP Status)

All metrics can be viewed by an arbitrary time window - defaults to `Last 24 Hours`.

Go to <a href="https://grafana-264e6f-test.apps.silver.devops.gov.bc.ca" target="_blank">Grafana</a> to view metrics for your configured services.

You can also access the metrics from the `API Services Portal`.

## 7. Grant access to others

The `acl` command provides a way to update the access for the namespace.  It expects an all-inclusive membership list, so the `--users` should have the full list of members.  Any user that is a member but not in the `--users` list will be removed from the namespace.

For elevated privileges (such as managing Service Accounts), add the usernames to the `--managers` argument.

```
gwa acl --users jjones@idir --managers acope@idir
```

The result will show the ACL changes.  The Add/Delete counts represent the membership changes of registered users.  The Missing count represents the users that will automatically be added to the namespace once they have logged into the `APS Services Portal`.

## 8. Add to your CI/CD Pipeline

Update your CI/CD pipelines to run the `gwa-cli` to keep your services updated on the gateway.

### Github Actions Example

In the repository that you maintain your CI/CD Pipeline configuration, use the Service Account details from `Step 2` to set up two `Secrets`:

* GWA_ACCT_ID

* GWA_ACCT_SECRET

Add a `.gwa` folder (can be called anything) that will be used to hold your gateway configuration.

The below example Github Workflow is for updating the `global` namespace:

```
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
    - env:
        GWA_NAMESPACE: global
      run: |
        curl -L -O https://bcgov.github.io/gwa-cli/gwa_v1.0.10_linux_x64.zip
        unzip gwa_v1.0.10_linux_x64.zip
        export PATH=$PATH:.

        cd ../.gwa/{$GWA_NAMESPACE}

        gwa init -T \
          --namespace=${GWA_NAMESPACE} \
          --client-id=${{ secrets.GWA_ACCT_ID }} \
          --client-secret=${{ secrets.GWA_ACCT_SECRET }}

        gwa pg

        gwa acl --users acope@idir --managers acope@idir

```
