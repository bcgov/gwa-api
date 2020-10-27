
import re

namespace_validation_rule='^[a-z][a-z0-9]{4,14}$'

host_validation_rule='[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*'

def namespace_valid(input_string):
    regex = re.compile(namespace_validation_rule)
    match = regex.match(str(input_string))
    return bool(match is not None)

def host_valid(input_string):
    return True
    # regex = re.compile(host_validation_rule)
    # match = regex.match(str(input_string))
    # return bool(match is not None)
