from string import Template

ROUTE = Template("""
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ${name}
  resourceVersion: "${resource_version}"
  annotations:
    haproxy.router.openshift.io/timeout: 30m
${data_class_annotation}
  labels:
    aps-generated-by: "gwa-cli"
    aps-published-on: "${fmt_time}"
    aps-namespace: "${ns}"
    aps-select-tag: "${select_tag}"
    aps-published-ts: "${timestamp}"
    aps-ssl: "${ssl_ref}"
    aps-data-plane: "${data_plane}"
    aps-template-version: "${template_version}"
spec:
  host: ${host}
  port:
    targetPort: kong-proxy
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
    certificate: |-
${ssl_crt}
    key: |-
${ssl_key}
  to:
    kind: Service
    name: ${service_name}
    weight: 100
  wildcardPolicy: None
status:
  ingress:
  - host: ${host}
    routerName: router
    wildcardPolicy: None 
""")

ROUTE_HEAD = Template("""
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ${name}

""")
