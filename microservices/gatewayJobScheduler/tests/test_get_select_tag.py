from app import get_select_tag

def test_happy_get_select_tag():
    tags = [ 'ns.NS1' ]
    assert get_select_tag(tags) == "ns.NS1"

def test_happy_get_select_tag_with_qualifier():
    tags = [ 'another', 'ns.NS1.dev' ]
    assert get_select_tag(tags) == "ns.NS1.dev"