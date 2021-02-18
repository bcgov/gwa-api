import re

from utils.validators import namespace_valid


def test_namespace_validator():
    assert namespace_valid("abc1234") == True
    assert namespace_valid("abc") == False, "Expecting Too Short"
    assert namespace_valid("1abcmore") == False, "Expecting Numerics"
    assert namespace_valid("abcmore") == True
    assert namespace_valid("thtoo-lon") == True, "Expecting Special Chars"
    assert namespace_valid("thisISbad") == False, "Expecting Uppercase"
