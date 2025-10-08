"""
Financial Modeling Prep (FMP) Provider - FUTURE IMPLEMENTATION

This is a placeholder showing exactly what needs to be implemented
when upgrading to a paid, production-ready API.

To activate this provider:
1. Sign up at https://financialmodelingprep.com/
2. Get API key
3. Implement the methods below following the examples
4. Set environment variable: DATA_PROVIDER=fmp
5. Set environment variable: FMP_API_KEY=your_key_here

Cost: $29/mo for 5,000 API calls/day (plenty for Stocknity)
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiohttp

from backend.services.data_sources.base_provider import (
    BaseDataProvider,
    DataProviderType,
    StockData
)

logger = logging.getLogger(__name__)


class FMPProvider(BaseDataProvider):
    """
    Financial Modeling Prep adapter implementing BaseDataProvider interface.
    
    IMPLEMENTATION GUIDE:
    
    FMP API Documentation: https://site.financialmodelingprep.com/developer/docs
    
    Endpoints you'll need:
    - /api/v3/profile/{ticker} - Company profile
    - /api/v3/ratios/{ticker} - Financial ratios
    - /api/v3/key-metrics/{ticker} - Key metrics
    - /api/v3/financial-growth/{ticker} - Growth rates
    
    Example API Call:
        GET https://financialmodelingprep.com/api/v3/profile/AAPL?apikey=YOUR_KEY
        
    Response Format:
        [{
            "symbol": "AAPL",
            "price": 150.00,
            "companyName": "Apple Inc",
            "sector": "Technology",
            ...
        }]
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FMP provider.
        
        Args:
            api_key: FMP API key (or set FMP_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('FMP_API_KEY')
        if not self.api_key:
            logger.warning("FMP_API_KEY not set. Provider will not work.")
        
        self.base_url = "https://financialmodelingprep.com/api/v3"
        self.session = None
    
    @property
    def provider_type(self) -> DataProviderType:
        return DataProviderType.FMP
    
    @property
    def rate_limit_per_minute(self) -> int:
        # FMP $29/mo tier: 5000 calls/day = ~3.5 calls/minute average
        # But allows bursts, so use 10/minute in practice
        return 10
    
    async def fetch_stock(self, ticker: str) -> Optional[StockData]:
        """
        Fetch stock data from Financial Modeling Prep.
        
        IMPLEMENTATION TEMPLATE:
        
        async with aiohttp.ClientSession() as session:
            # 1. Get company profile
            profile_url = f"{self.base_url}/profile/{ticker}?apikey={self.api_key}"
            async with session.get(profile_url) as response:
                profile_data = await response.json()
            
            # 2. Get financial ratios
            ratios_url = f"{self.base_url}/ratios/{ticker}?apikey={self.api_key}"
            async with session.get(ratios_url) as response:
                ratios_data = await response.json()
            
            # 3. Get key metrics
            metrics_url = f"{self.base_url}/key-metrics/{ticker}?apikey={self.api_key}"
            async with session.get(metrics_url) as response:
                metrics_data = await response.json()
            
            # 4. Get financial growth
            growth_url = f"{self.base_url}/financial-growth/{ticker}?apikey={self.api_key}"
            async with session.get(growth_url) as response:
                growth_data = await response.json()
            
            # 5. Combine all data into StockData format
            return StockData(
                ticker=profile_data[0]['symbol'],
                name=profile_data[0]['companyName'],
                sector=profile_data[0]['sector'],
                industry=profile_data[0]['industry'],
                current_price=profile_data[0]['price'],
                market_cap=profile_data[0]['mktCap'],
                pe_ratio=ratios_data[0]['priceEarningsRatio'],
                pb_ratio=ratios_data[0]['priceToBookRatio'],
                peg_ratio=ratios_data[0]['priceEarningsToGrowthRatio'],
                roe=ratios_data[0]['returnOnEquity'],
                roa=ratios_data[0]['returnOnAssets'],
                net_margin=ratios_data[0]['netProfitMargin'],
                gross_margin=ratios_data[0]['grossProfitMargin'],
                operating_margin=ratios_data[0]['operatingProfitMargin'],
                debt_to_equity=ratios_data[0]['debtEquityRatio'],
                current_ratio=ratios_data[0]['currentRatio'],
                quick_ratio=ratios_data[0]['quickRatio'],
                earnings_growth=growth_data[0]['epsgrowth'],
                revenue_growth=growth_data[0]['revenueGrowth'],
                dividend_yield=metrics_data[0]['dividendYield'],
                eps=profile_data[0]['eps'],
                book_value_per_share=metrics_data[0]['bookValuePerShare'],
                source='fmp',
                fetched_at=datetime.now().isoformat()
            )
        """
        raise NotImplementedError(
            "FMP provider not yet implemented. "
            "When ready to upgrade from free tier:\n"
            "1. Sign up at https://financialmodelingprep.com/ ($29/mo)\n"
            "2. Get API key\n"
            "3. Implement this method using the template above\n"
            "4. Set FMP_API_KEY environment variable\n"
            "5. Set DATA_PROVIDER=fmp in config"
        )
    
    async def fetch_stocks_batch(self, tickers: List[str]) -> Dict[str, Optional[StockData]]:
        """
        Fetch multiple stocks from FMP.
        
        FMP has batch endpoints that are more efficient!
        
        IMPLEMENTATION TEMPLATE:
        
        # FMP allows comma-separated tickers in one call:
        ticker_string = ','.join(tickers)
        url = f"{self.base_url}/profile/{ticker_string}?apikey={self.api_key}"
        
        # This fetches ALL stocks in ONE API call!
        # Much more efficient than Yahoo
        """
        raise NotImplementedError("See fetch_stock() for implementation guide")
    
    async def search_by_sector(self, sector: str, limit: int = 50) -> List[StockData]:
        """
        Get stocks in a specific sector from FMP.
        
        FMP has a sector screener endpoint!
        
        IMPLEMENTATION TEMPLATE:
        
        url = f"{self.base_url}/stock-screener"
        params = {
            'sector': sector,
            'limit': limit,
            'apikey': self.api_key
        }
        
        # FMP can return stocks filtered by sector directly
        """
        raise NotImplementedError("See fetch_stock() for implementation guide")
    
    async def validate_ticker(self, ticker: str) -> bool:
        """Check if ticker exists in FMP"""
        # FMP has a search endpoint
        raise NotImplementedError("See fetch_stock() for implementation guide")
    
    def get_cost_estimate(self, operations: Dict[str, int]) -> Dict[str, Any]:
        """
        Get cost estimate for FMP API.
        
        This actually works! Shows what your operations will cost.
        """
        fetch_count = operations.get('fetch_stock', 0)
        batch_count = operations.get('fetch_batch', 0)
        
        # FMP uses 4 API calls per stock for full data
        calls_per_stock = 4
        
        # But batch operations can use 1 call for multiple stocks
        batch_efficiency = 0.5  # Batching saves ~50% of calls
        
        total_calls = (fetch_count * calls_per_stock) + (batch_count * calls_per_stock * batch_efficiency)
        
        # Pricing tiers
        daily_limit_free = 250
        daily_limit_starter = 5000  # $29/mo
        daily_limit_professional = 10000  # $79/mo
        
        # Determine required tier
        if total_calls <= daily_limit_free:
            tier = "Free"
            cost = 0
        elif total_calls <= daily_limit_starter:
            tier = "Starter"
            cost = 29
        elif total_calls <= daily_limit_professional:
            tier = "Professional"
            cost = 79
        else:
            tier = "Enterprise (contact sales)"
            cost = 200  # Estimate
        
        return {
            'provider': 'Financial Modeling Prep',
            'total_calls': int(total_calls),
            'calls_per_day': int(total_calls),
            'cost_usd_monthly': cost,
            'tier': tier,
            'daily_limit': daily_limit_starter if tier == "Starter" else daily_limit_free,
            'within_limits': total_calls <= daily_limit_starter,
            'website': 'https://financialmodelingprep.com/pricing',
            'recommendation': f"{'Current tier sufficient' if total_calls < daily_limit_starter else 'Consider upgrading tier'}"
        }


# Example usage (when implemented):
"""
# In your config or .env:
DATA_PROVIDER=fmp
FMP_API_KEY=your_key_here

# In your code:
from backend.services.data_sources.base_provider import DataProviderFactory, DataProviderType

# Automatic based on config:
provider = DataProviderFactory.create(DataProviderFactory.get_recommended_provider())

# Or explicit:
provider = DataProviderFactory.create(DataProviderType.FMP, api_key="your_key")

# Use it (same interface as Yahoo!):
data = await provider.fetch_stock('AAPL')
print(f"{data.ticker}: ${data.current_price:.2f}, ROE: {data.roe:.2%}")

# That's it! No other code changes needed!
"""

