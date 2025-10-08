"""
Data Sources Package

This package contains modules for fetching stock data from various sources:
- Yahoo Finance: Primary source for stock fundamentals
- Alpha Vantage: Fallback for when Yahoo fails
- Financial Modeling Prep: Alternative fundamentals source

The DataAggregator class intelligently tries multiple sources with caching.

Features:
- Concurrent batch fetching (10x faster than sequential)
- Sector-based screening and filtering
- Redis caching with fallback
- Rate limiting protection
"""

from backend.services.data_sources.yahoo_finance import fetch_stock_data_yahoo
from backend.services.data_sources.aggregator import DataAggregator
from backend.services.data_sources.sector_screener import (
    get_tickers_by_sector,
    get_sector_for_ticker,
    get_all_sectors,
    filter_tickers_by_sectors,
    get_sector_diversification,
    get_popular_stocks_by_sector
)

__all__ = [
    'fetch_stock_data_yahoo',
    'DataAggregator',
    'get_tickers_by_sector',
    'get_sector_for_ticker',
    'get_all_sectors',
    'filter_tickers_by_sectors',
    'get_sector_diversification',
    'get_popular_stocks_by_sector'
]

