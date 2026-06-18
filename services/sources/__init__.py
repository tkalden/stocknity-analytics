import os
from services.sources.base import StockDataSource, FetchResult


def get_data_source() -> StockDataSource:
    """
    Factory — swap source via STOCK_DATA_SOURCE env var.
    Values: fmp | massive | yfinance
    """
    source = os.getenv("STOCK_DATA_SOURCE", "fmp").lower()

    if source == "fmp":
        from services.sources.fmp import FMPDataSource
        return FMPDataSource()

    if source == "massive":
        from services.sources.massive import MassiveDataSource
        return MassiveDataSource()

    if source == "yfinance":
        from services.sources.yfinance_source import YFinanceDataSource
        return YFinanceDataSource()

    raise ValueError(f"Unknown STOCK_DATA_SOURCE: {source!r}. Use fmp | massive | yfinance")


__all__ = ["get_data_source", "StockDataSource", "FetchResult"]
