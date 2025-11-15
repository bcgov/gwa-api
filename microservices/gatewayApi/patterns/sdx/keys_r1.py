
from string import Template
import textwrap

###
### Keys
###
###
template = Template("""
_format_version: "3.0"
keys:
  - name: ${key_name}
    kid: ${kid}
    pem:
      public_key: |-
${public_key_pem}
    tags: [ns.${gateway}.${ns_qualifier}]
""")

def eval_keys_pattern (context):
  pem = context["public_key_pem"]
  context["public_key_pem"] = textwrap.indent(context["public_key_pem"], "        ")
  return template.substitute(context)
