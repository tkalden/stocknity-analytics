#!/usr/bin/env python3
"""
Tests for the read-only strength calculation path.

Verifies that:
1. StrengthCalculator.calculate_strength_value reads the canonical
   stock_data:{index}:{sector} key, computes strength in-memory, and returns a
   valid DataFrame WITHOUT writing anything back to Redis.
2. A missing/empty canonical key raises CanonicalDataUnavailable and the
   optimizer endpoint surfaces HTTP 503.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.strengthCalculator import StrengthCalculator, CanonicalDataUnavailable, CANONICAL_COLUMNS


def _canonical_fixture():
    """A canonical stock_data:* DataFrame with the documented schema."""
    rows = []
    tickers = ["AAPL", "MSFT", "JNJ", "KO", "PG"]
    for i, t in enumerate(tickers):
        rows.append({
            "Ticker": t,
            "pe": 15 + i,
            "pb": 2 + i * 0.1,
            "fpe": 14 + i,
            "peg": 1.2 + i * 0.1,
            "dividend": 0.02 + i * 0.001,
            "annual_return": 0.10 + i * 0.01,
            "today_change": 0.5 - i * 0.1,
            "price": 100 + i * 10,
            "beta": 1.0 + i * 0.05,
            "roi": 0.1,
            "roe": 0.2,
            "insider_own": 0.01,
        })
    return pd.DataFrame(rows)


def _returns_fixture(tickers):
    """Annual-return enrichment frame keyed by Ticker (no Redis write needed)."""
    return pd.DataFrame({
        "Ticker": tickers,
        "expected_annual_return": [0.12] * len(tickers),
        "expected_annual_risk": [0.30] * len(tickers),
        "return_risk_ratio": [0.40] * len(tickers),
    })


def test_calculate_strength_reads_canonical_and_does_not_write():
    """calculate_strength_value returns a valid DataFrame and never writes."""
    canonical = _canonical_fixture()

    mock_redis = MagicMock()
    mock_redis.get_stock_data.return_value = canonical

    # Avoid network: return enrichment data directly from the annual-return path.
    with patch("services.strengthCalculator.redis_manager", mock_redis), \
         patch("services.annualReturn.AnnualReturn.get_annual_return_data",
               return_value=_returns_fixture(canonical["Ticker"].tolist())):
        calc = StrengthCalculator()
        result = calc.calculate_strength_value(
            stock_type="Value", sector="Any", index="S&P 500"
        )

    # (1) valid DataFrame with computed strength
    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    assert "strength" in result.columns
    assert "Ticker" in result.columns

    # Confirms it read the canonical key
    mock_redis.get_stock_data.assert_called_once_with("S&P 500", "Any")

    # (2) NO save_* method was called on redis_manager
    mock_redis.save_strength_data.assert_not_called()
    mock_redis.save_stock_data.assert_not_called()
    mock_redis.save_annual_returns.assert_not_called()
    # Generic guard: nothing that looks like a write was invoked.
    for name, called_mock in mock_redis._mock_children.items():
        if name.startswith("save_"):
            called_mock.assert_not_called()


def test_missing_canonical_key_raises():
    """An empty canonical key raises CanonicalDataUnavailable."""
    mock_redis = MagicMock()
    mock_redis.get_stock_data.return_value = pd.DataFrame()

    with patch("services.strengthCalculator.redis_manager", mock_redis):
        calc = StrengthCalculator()
        with pytest.raises(CanonicalDataUnavailable):
            calc.calculate_strength_value(
                stock_type="Value", sector="Any", index="S&P 500"
            )
    mock_redis.save_stock_data.assert_not_called()
    mock_redis.save_strength_data.assert_not_called()


def test_malformed_canonical_key_raises():
    """A canonical key missing documented columns raises CanonicalDataUnavailable."""
    bad = pd.DataFrame({"Ticker": ["AAPL"], "price": [100]})  # missing most columns
    mock_redis = MagicMock()
    mock_redis.get_stock_data.return_value = bad

    with patch("services.strengthCalculator.redis_manager", mock_redis):
        calc = StrengthCalculator()
        with pytest.raises(CanonicalDataUnavailable):
            calc.calculate_strength_value(
                stock_type="Value", sector="Any", index="S&P 500"
            )


def test_advanced_optimizer_endpoint_returns_503_on_missing_canonical():
    """The /api/portfolio/advanced endpoint returns 503 when canonical data is missing."""
    os.environ.pop("INTERNAL_SECRET", None)  # dev mode: gate disabled
    os.environ.pop("FLASK_ENV", None)

    from core import create_app
    app = create_app()
    client = app.test_client()

    with patch.object(
        StrengthCalculator,
        "calculate_strength_value",
        side_effect=CanonicalDataUnavailable("stock_data:S&P 500:Any is missing or empty"),
    ):
        resp = client.post("/api/portfolio/advanced", json={
            "method": "markowitz",
            "investing_amount": 10000,
            "max_stock_price": 100,
            "risk_tolerance": "Medium",
            "sector": "Any",
            "index": "S&P 500",
            "stock_type": "Value",
        })

    assert resp.status_code == 503
    body = resp.get_json()
    assert body["success"] is False
    assert "Market data not yet available" in body["error"]


def test_canonical_columns_documented():
    """The documented schema matches the CLAUDE.md DataFrame schema."""
    assert CANONICAL_COLUMNS == [
        "Ticker", "pe", "pb", "fpe", "peg",
        "dividend", "annual_return", "today_change", "price",
    ]
