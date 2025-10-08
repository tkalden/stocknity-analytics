"""
Data Provider Adapters

This package contains adapter implementations for different data sources.
Each adapter implements the BaseDataProvider interface.

Available Providers:
- YahooFinanceProvider: Free, unofficial, good for development
- FinvizProvider: Free, web scraping, good for screening
- FMPProvider: Paid ($29/mo), official API, production-ready (TODO)
- AlphaVantageProvider: Paid ($49/mo), official API (TODO)
"""

from backend.services.data_sources.base_provider import (
    BaseDataProvider,
    DataProviderType,
    DataProviderFactory,
    StockData
)

__all__ = [
    'BaseDataProvider',
    'DataProviderType',
    'DataProviderFactory',
    'StockData'
]

