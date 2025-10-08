"""
Yahoo Finance Provider Adapter

Adapts Yahoo Finance (yfinance) to our standardized interface.

Pros:
- Free
- Good data coverage
- Real-time prices

Cons:
- Unofficial (web scraping)
- Rate limited
- Can break without notice
- Not suitable for production at scale

Use for: Development, MVP validation
Upgrade to: FMP or Alpha Vantage for production
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.services.data_sources.base_provider import (
    BaseDataProvider,
    DataProviderType,
    StockData
)
from backend.services.data_sources.yahoo_finance import fetch_stock_data_yahoo

logger = logging.getLogger(__name__)


class YahooFinanceProvider(BaseDataProvider):
    """
    Yahoo Finance adapter implementing BaseDataProvider interface.
    
    Example:
        >>> provider = YahooFinanceProvider()
        >>> data = await provider.fetch_stock('AAPL')
        >>> print(f"{data.ticker}: ${data.current_price:.2f}")
        AAPL: $150.00
    """
    
    @property
    def provider_type(self) -> DataProviderType:
        return DataProviderType.YAHOO
    
    @property
    def rate_limit_per_minute(self) -> int:
        # Yahoo's unofficial limit is ~10 requests/minute
        return 10
    
    async def fetch_stock(self, ticker: str) -> Optional[StockData]:
        """
        Fetch stock data from Yahoo Finance.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            StockData object or None if fetch fails
        """
        try:
            # Use our existing Yahoo Finance fetcher
            raw_data = fetch_stock_data_yahoo(ticker)
            
            if not raw_data:
                logger.warning(f"No data returned from Yahoo for {ticker}")
                return None
            
            # Adapt Yahoo's format to our standardized StockData format
            return StockData(
                ticker=raw_data.get('ticker', ticker.upper()),
                name=raw_data.get('name', ticker),  # Yahoo doesn't always have name
                sector=raw_data.get('sector', 'Unknown'),
                industry=raw_data.get('industry', 'Unknown'),
                current_price=raw_data.get('current_price', 0.0),
                market_cap=raw_data.get('market_cap', 0.0),
                pe_ratio=raw_data.get('pe_ratio', 0.0),
                pb_ratio=raw_data.get('pb_ratio', 0.0),
                peg_ratio=raw_data.get('peg_ratio', 0.0),
                roe=raw_data.get('roe', 0.0),
                roa=raw_data.get('roa', 0.0),  # May need to calculate from Yahoo data
                net_margin=raw_data.get('net_margin', 0.0),
                gross_margin=raw_data.get('gross_margin', 0.0),
                operating_margin=raw_data.get('operating_margin', 0.0),
                debt_to_equity=raw_data.get('debt_to_equity', 0.0),
                current_ratio=raw_data.get('current_ratio', 0.0),
                quick_ratio=raw_data.get('quick_ratio', 0.0),
                earnings_growth=raw_data.get('earnings_growth', 0.0),
                revenue_growth=raw_data.get('revenue_growth', 0.0),
                dividend_yield=raw_data.get('dividend_yield', 0.0),
                eps=raw_data.get('eps', 0.0),
                book_value_per_share=raw_data.get('book_value', 0.0),
                source='yahoo',
                fetched_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error fetching {ticker} from Yahoo: {e}")
            return None
    
    async def fetch_stocks_batch(self, tickers: List[str]) -> Dict[str, Optional[StockData]]:
        """
        Fetch multiple stocks from Yahoo Finance.
        
        Note: Yahoo doesn't have a true batch API, so we fetch sequentially
        with rate limiting. For production, consider upgrading to FMP.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            Dictionary mapping ticker -> StockData
        """
        import asyncio
        
        results = {}
        
        # Fetch with delay to respect rate limits
        for ticker in tickers:
            results[ticker] = await self.fetch_stock(ticker)
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.2)  # 5 stocks/second
        
        return results
    
    async def search_by_sector(self, sector: str, limit: int = 50) -> List[StockData]:
        """
        Get stocks in a specific sector.
        
        Note: Yahoo doesn't provide sector screening.
        For production, use Finviz (current) or FMP (paid).
        
        Args:
            sector: Sector name
            limit: Max stocks to return
            
        Returns:
            Empty list (not supported by Yahoo)
        """
        logger.warning("Yahoo Finance doesn't support sector screening. Use Finviz or upgrade to FMP.")
        return []
    
    async def validate_ticker(self, ticker: str) -> bool:
        """
        Check if ticker exists.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            True if ticker is valid
        """
        from backend.services.data_sources.yahoo_finance import validate_ticker
        return validate_ticker(ticker)
    
    def get_cost_estimate(self, operations: Dict[str, int]) -> Dict[str, Any]:
        """
        Get cost estimate for Yahoo Finance.
        
        Args:
            operations: Dict of operation counts
            
        Returns:
            Cost info (Yahoo is free but rate-limited)
        """
        fetch_count = operations.get('fetch_stock', 0)
        batch_count = operations.get('fetch_batch', 0)
        
        total_calls = fetch_count + (batch_count * 10)  # Assume 10 stocks per batch
        
        return {
            'provider': 'Yahoo Finance',
            'total_calls': total_calls,
            'cost_usd': 0.0,
            'tier': 'Free (unofficial)',
            'daily_limit': 'Unknown (~2000 calls/day before rate limiting)',
            'within_limits': total_calls < 2000,
            'warning': 'Yahoo Finance is unofficial and may break. Not recommended for production.',
            'recommendation': 'For production, upgrade to Financial Modeling Prep ($29/mo) or Alpha Vantage ($49/mo)'
        }

