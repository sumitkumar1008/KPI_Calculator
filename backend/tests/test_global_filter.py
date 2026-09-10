"""
Tests for Global Filter Service & API Routes
"""

from app.services.global_filter_service import (
    get_available_filter_options,
    validate_and_normalize_filters,
)


def test_validate_and_normalize_filters_defaults():
    filters = validate_and_normalize_filters(None)
    assert filters["period"] == "daily"
    assert filters["search"] == ""


def test_validate_and_normalize_filters_valid():
    filters = validate_and_normalize_filters({"period": "weekly", "search": "  INC123  "})
    assert filters["period"] == "weekly"
    assert filters["search"] == "INC123"

    filters_monthly = validate_and_normalize_filters({"period": "MONTHLY"})
    assert filters_monthly["period"] == "monthly"


def test_validate_and_normalize_filters_invalid_period_fallback():
    filters = validate_and_normalize_filters({"period": "yearly"})
    assert filters["period"] == "daily"


def test_get_available_filter_options():
    opts = get_available_filter_options()
    assert "periods" in opts
    assert len(opts["periods"]) == 3
    assert opts["default_period"] == "daily"


def test_global_filter_api_endpoints(client):
    res_opts = client.get("/api/v1/kpi/global-filter/options")
    assert res_opts.status_code == 200
    json_opts = res_opts.get_json()
    assert json_opts["default_period"] == "daily"

    res_val = client.post(
        "/api/v1/kpi/global-filter/validate",
        json={"period": "monthly"},
    )
    assert res_val.status_code == 200
    json_val = res_val.get_json()
    assert json_val["success"] is True
    assert json_val["filters"]["period"] == "monthly"
