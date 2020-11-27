
# Upstream Services Migrating from OCP3 to OCP4

## What do I need to do to setup my Service on the new APS Gateway?

### Configure APS Gateway

As part of migrating your service to OCP4, you will need to prepare the Gateway configuration for your Service. An example of what it would look like:

```
services:
- host: <my_ocp4_service>.<my_ocp4_namespace>.svc
  name: apidata-ocp-https-kirk-jobs
  port: 80
  protocol: http
```

The routes will have a minor change by no longer using the `https` protocol as SSL termination will be performed at the `OCP4 Edge` and the traffic to the `APS Gateway` will be unencrypted:

```
  routes:
  - hosts:
    - kirk.data.gov.bc.ca
    protocols:
    - http
```

Apply your changes to the `APS Gateway` by running the `gwa pg` command.

### Remove all Routes/Ingress

Your `Pod Service` does not need to have an external route because the `APS Gateway` is acting as the entry point for your service.  So you should ensure that you do not have any routes that have the host as `*.api.gov.bc.ca`, `*.data.gov.bc.ca`, or `*.apps.gov.bc.ca`.  Having routes with these hosts will conflict with the routes that the `APS Gateway` will create automatically based on your configuration.  It is ok to create routes under the `.apps.silver.devops.gov.bc.ca` domain for dev/testing.

### Regression test your Service

Regression testing is being performed in the `APS Gateway` test environment.  When you apply your changes in the test environment, your routing URLs are transformed into a custom vanity domain.

For example, a route for `kirk.data.gov.bc.ca` results in a public route:

`https://kirk-data-gov-bc-ca.test.apsgw.xyz`

This is what you will use to peform your regression testing.  To find out the exact public route for your services, go to the `Services` tab on the `APS Services Portal`.


### Switch production traffic to your OCP4 Service

When the Production instance of the `APS Gateway` is ready, communication will go out to the teams as additional tasks will be required to enable the service on our Production environment:

| Task                                                     | Responsibility | 
| -------------------------------------------------------- | -------------- |
| Create namespace and service account | API Owner |
| Apply configuration (either in your CI/CD pipeline, or manually) | API Owner |
| Update `Kong14` service upstream host from `https://142.34.143.180` to `https://142.34.194.118` | APS Team
| Decommission OCP3 projects | API Owner |

### Final big-bang switchover

At the completion of regression testing, a big-bang switchover to the new APS Gateway will be performed by updating the DNS to point to OCP4 Edge.

| Task                                                     | Responsibility | 
| -------------------------------------------------------- | -------------- |
| Ownership of the Gateway configuration transitioned to Service teams | API Owners
| Update DNS for *.api.gov.bc.ca, *.data.gov.bc.ca to point to 142.34.194.118       | APS Team |
| 

At the time of switchover, we expect that there will be a mix of services running on OCP3, running on OCP4, running on DataBC Servers and running on external cloud.  But the expectation is that all the teams will have ownership of the Gateway configuration for their respective Services, and empowered to do ongoing changes.


# Appendix

## Terminology

* `WAM` : Web Application Management
* `Kong14` : The current Kong 0.14 implementation run on Data BC infrastructure (142.34.140.8, 142.34.5.17)
* `APS Gateway` : The new Kong 2.1.x implementation run on Openshift Container Platform V4 (OCP4)
* `OCP3 Edge` : The OCP3 Edge server (142.34.208.209, more known as *.pathfinder.gov.bc.ca, or 142.34.143.180, more known as *.pathfinder.bcgov)
* `OCP4 Edge` : The OCP4 Edge server (142.34.194.118), more known as *.apps.silver.devops.gov.bc.ca)
* `Pod Service` : The actual Kubernetes Service that is run within your Pod (`oc get services`)
* `OCP3 Route` : A Route on the OCP3 Edge that is the relationship between your Pod Service and the OCP3 Edge

## How it works currently

Current (Oct 2020) flow for `*.api.gov.bc.ca` and `*.data.gov.bc.ca` domains where the upstream is on OCP3, is:

`Internet` -> `Kong14` -> `OCP3 Edge` -> `Pod Service`

On `Kong14`, a Service example looks something like this and is administered via email to David or Craig, and they use Konga:

```
services:
- host: 142.34.143.180
  name: apidata-ocp-https-kirk-jobs
  port: 443
  protocol: https
```

With the route:

```
  routes:
  - hosts:
    - kirk.data.gov.bc.ca
    protocols:
    - http
    - https
```

The `kirk` team is then responsible for creating an `OCP3 Route` and the `Pod Service`.

