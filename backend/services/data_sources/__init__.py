"""
Data Sources Package

This package contains modules for fetching stock data from various sources:
- Yahoo Finance: Primary source for stock fundamentals
- Alpha Vantage: Fallback for when Yahoo fails
- Financial Modeling Prep: Alternative fundamentals source

The DataAggregator class intelligently tries multiple sources with caching.
"""

from backend.services.data_sources.yahoo_finance import fetch_stock_data_yahoo
from backend.services.data_sources.aggregator import DataAggregator

__all__ = ['fetch_stock_data_yahoo', 'DataAggregator']

