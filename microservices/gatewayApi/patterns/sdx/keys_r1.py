
from string import Template

###
### Keys
###
###
template = Template("""
_format_version: "3.0"
keys:
  - name: ${key_name}
    kid: ${kid}
    tags: [ns.${gateway}.${ns_qualifier}]
    pem:
      public_key: ${public_key_pem}    
""")

def eval_keys_pattern (context):
  context["public_key_pem"] = repr(context["public_key_pem"])
  return template.substitute(context)
