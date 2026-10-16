import pytest
from app import ensure_routes_present


def test_empty_route_list_raises():
    # Syncing an empty list would delete every route in every namespace
    with pytest.raises(ValueError, match="zero routes"):
        ensure_routes_present([])


def test_routes_present():
    ensure_routes_present([{"name": "route-1", "tags": ["ns.ns1"], "hosts": ["test.api.gov.bc.ca"]}])
