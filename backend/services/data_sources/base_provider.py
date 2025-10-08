"""
Abstract Data Provider Interface

This module defines the interface that all data providers must implement.
This allows easy swapping between Finviz, Yahoo, FMP, Alpha Vantage, etc.

Design Pattern: Adapter Pattern
- Each provider adapts their API to our standardized interface
- Business logic only depends on this interface
- Swap providers by changing config, not code!
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class DataProviderType(Enum):
    """Available data provider types"""
    FINVIZ = "finviz"
    YAHOO = "yahoo"
    FMP = "fmp"  # Financial Modeling Prep (future)
    ALPHA_VANTAGE = "alpha_vantage"  # (future)
    POLYGON = "polygon"  # (future)


@dataclass
class StockData:
    """
    Standardized stock data format.
    All providers must return data in this format.
    """
    # Basic info
    ticker: str
    name: str
    sector: str
    industry: str
    
    # Price data
    current_price: float
    market_cap: float
    
    # Valuation metrics
    pe_ratio: float
    pb_ratio: float
    peg_ratio: float
    
    # Profitability metrics
    roe: float  # Return on equity (as decimal, e.g., 0.25 = 25%)
    roa: float  # Return on assets (as decimal)
    net_margin: float  # Net profit margin (as decimal)
    gross_margin: float  # Gross margin (as decimal)
    operating_margin: float  # Operating margin (as decimal)
    
    # Financial health
    debt_to_equity: float
    current_ratio: float
    quick_ratio: float
    
    # Growth metrics
    earnings_growth: float  # EPS growth (as decimal)
    revenue_growth: float  # Revenue growth (as decimal)
    
    # Dividend
    dividend_yield: float  # As decimal
    
    # Per-share data
    eps: float  # Earnings per share
    book_value_per_share: float
    
    # Metadata
    source: str  # Which provider supplied this data
    fetched_at: str  # ISO timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'ticker': self.ticker,
            'name': self.name,
            'sector': self.sector,
            'industry': self.industry,
            'current_price': self.current_price,
            'market_cap': self.market_cap,
            'pe_ratio': self.pe_ratio,
            'pb_ratio': self.pb_ratio,
            'peg_ratio': self.peg_ratio,
            'roe': self.roe,
            'roa': self.roa,
            'net_margin': self.net_margin,
            'gross_margin': self.gross_margin,
            'operating_margin': self.operating_margin,
            'debt_to_equity': self.debt_to_equity,
            'current_ratio': self.current_ratio,
            'quick_ratio': self.quick_ratio,
            'earnings_growth': self.earnings_growth,
            'revenue_growth': self.revenue_growth,
            'dividend_yield': self.dividend_yield,
            'eps': self.eps,
            'book_value_per_share': self.book_value_per_share,
            'source': self.source,
            'fetched_at': self.fetched_at
        }


class BaseDataProvider(ABC):
    """
    Abstract base class for all data providers.
    
    All data sources (Finviz, Yahoo, FMP, etc.) must implement this interface.
    This ensures we can swap providers without changing business logic.
    
    Example:
        >>> provider = YahooFinanceProvider()
        >>> data = await provider.fetch_stock('AAPL')
        >>> print(f"ROE: {data.roe:.2%}")
    """
    
    @property
    @abstractmethod
    def provider_type(self) -> DataProviderType:
        """Return the provider type"""
        pass
    
    @property
    @abstractmethod
    def rate_limit_per_minute(self) -> int:
        """Return the rate limit for this provider"""
        pass
    
    @abstractmethod
    async def fetch_stock(self, ticker: str) -> Optional[StockData]:
        """
        Fetch data for a single stock.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            StockData object or None if fetch fails
        """
        pass
    
    @abstractmethod
    async def fetch_stocks_batch(self, tickers: List[str]) -> Dict[str, Optional[StockData]]:
        """
        Fetch data for multiple stocks.
        
        Some providers may optimize this (true batch API).
        Others will loop internally (still better than external loops).
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            Dictionary mapping ticker -> StockData (or None if failed)
        """
        pass
    
    @abstractmethod
    async def search_by_sector(self, sector: str, limit: int = 50) -> List[StockData]:
        """
        Get stocks in a specific sector.
        
        Args:
            sector: Sector name (e.g., 'Technology', 'Healthcare')
            limit: Maximum number of stocks to return
            
        Returns:
            List of StockData objects
        """
        pass
    
    @abstractmethod
    async def validate_ticker(self, ticker: str) -> bool:
        """
        Check if a ticker exists and is tradable.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            True if ticker is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_cost_estimate(self, operations: Dict[str, int]) -> Dict[str, Any]:
        """
        Estimate API costs for planned operations.
        
        Helps with cost planning and provider selection.
        
        Args:
            operations: Dict like {'fetch_stock': 100, 'fetch_batch': 10}
            
        Returns:
            Dict with cost estimate and limits info
            
        Example:
            >>> provider = FMPProvider()
            >>> cost = provider.get_cost_estimate({'fetch_stock': 500})
            >>> print(f"Daily calls: {cost['total_calls']}")
        """
        pass


class DataProviderFactory:
    """
    Factory for creating data provider instances.
    
    This is where you swap providers by changing config!
    
    Example:
        # In config.py:
        PRIMARY_PROVIDER = DataProviderType.YAHOO
        FALLBACK_PROVIDER = DataProviderType.FINVIZ
        
        # In code:
        provider = DataProviderFactory.create(PRIMARY_PROVIDER)
        data = await provider.fetch_stock('AAPL')
    """
    
    @staticmethod
    def create(provider_type: DataProviderType, **kwargs) -> BaseDataProvider:
        """
        Create a data provider instance.
        
        Args:
            provider_type: Type of provider to create
            **kwargs: Provider-specific configuration
            
        Returns:
            Data provider instance
            
        Raises:
            ValueError: If provider type is not implemented
        """
        if provider_type == DataProviderType.YAHOO:
            from backend.services.data_sources.providers.yahoo_provider import YahooFinanceProvider
            return YahooFinanceProvider(**kwargs)
        
        elif provider_type == DataProviderType.FINVIZ:
            from backend.services.data_sources.providers.finviz_provider import FinvizProvider
            return FinvizProvider(**kwargs)
        
        elif provider_type == DataProviderType.FMP:
            # Future implementation
            raise NotImplementedError(
                "FMP provider not yet implemented. "
                "When ready to upgrade, implement FMPProvider following BaseDataProvider interface."
            )
        
        elif provider_type == DataProviderType.ALPHA_VANTAGE:
            # Future implementation
            raise NotImplementedError("Alpha Vantage provider not yet implemented")
        
        elif provider_type == DataProviderType.POLYGON:
            # Future implementation
            raise NotImplementedError("Polygon provider not yet implemented")
        
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
    
    @staticmethod
    def get_recommended_provider() -> DataProviderType:
        """
        Get the recommended provider based on current configuration.
        
        This allows easy switching between dev/staging/prod environments.
        
        Returns:
            Recommended provider type
        """
        import os
        
        # Check environment variable
        provider_env = os.getenv('DATA_PROVIDER', 'yahoo').lower()
        
        provider_map = {
            'yahoo': DataProviderType.YAHOO,
            'finviz': DataProviderType.FINVIZ,
            'fmp': DataProviderType.FMP,
            'alpha_vantage': DataProviderType.ALPHA_VANTAGE,
            'polygon': DataProviderType.POLYGON
        }
        
        return provider_map.get(provider_env, DataProviderType.YAHOO)

