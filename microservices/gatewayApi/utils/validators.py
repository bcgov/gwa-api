
import re

namespace_validation_rule='^[a-z][a-z0-9]{4,14}'

def namespace_validation(input_string):
    regex = re.compile(namespace_validation_rule, re.I)
    match = regex.match(str(input_string))
    return bool(match == False)
