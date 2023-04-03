from string import Template

SERVICE = Template("""
apiVersion: v1
kind: Service
metadata:
  name: ${name}
  resourceVersion: "${resource_version}"
  annotations:
    service.beta.openshift.io/serving-cert-secret-name: "${secret_name}"
  labels:
    aps-generated-by: "gwa-cli"
    aps-published-on: "${fmt_time}"
    aps-namespace: "${ns}"
    aps-select-tag: "${select_tag}"
    aps-published-ts: "${timestamp}"
    aps-data-plane: "${data_plane}"
spec:
  ports:
    - name: kong-proxy-tls
      protocol: TCP
      port: 443
      targetPort: 8443
  type: ClusterIP
  selector:
    app.kubernetes.io/component: app
    app.kubernetes.io/instance: dp-silver
    app.kubernetes.io/name: kong
""")

SERVICE_HEAD = Template("""
apiVersion: v1
kind: Service
metadata:
  name: ${name}

""")
