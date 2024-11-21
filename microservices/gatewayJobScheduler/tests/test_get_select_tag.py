from app import _get_select_tag

def test_happy_get_select_tag():
    tags = [ 'ns.NS1' ]
    assert _get_select_tag(tags) == "ns.NS1"

def test_happy_get_select_tag_with_qualifier():
    tags = [ 'another', 'ns.NS1.dev' ]
    assert _get_select_tag(tags) == "ns.NS1.dev"