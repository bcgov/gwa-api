import re

namespace_validation_rule='^[a-z][a-z0-9]{4,14}$'

def namespace_valid(input_string):
    regex = re.compile(namespace_validation_rule)
    match = regex.match(str(input_string))
    return bool(match is not None)


assert namespace_valid("abc1234") == True
assert namespace_valid("abc") == False, "Expecting Too Short"
assert namespace_valid("1abcmore") == False, "Expecting Numerics"
assert namespace_valid("abcmore") == True
assert namespace_valid("thtoo-lon") == False, "Expecting Special Chars"
assert namespace_valid("thisISbad") == False, "Expecting Uppercase"
