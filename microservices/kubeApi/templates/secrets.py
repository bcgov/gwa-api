from string import Template

SECRET = Template("""
apiVersion: v1
kind: Secret
type: Opaque
metadata:
  name: ${name}
  annotations:
  labels:
    aps-generated-by: "gwa-cli"
    aps-published-on: "${fmt_time}"
    aps-namespace: "${ns}"
    aps-select-tag: "${select_tag}"
    aps-published-ts: "${timestamp}"
data:
  config: "${config}"
""")

SECRET_HEAD = Template("""
apiVersion: v1
kind: Secret
type: Opaque
metadata:
  name: ${name}
""")
