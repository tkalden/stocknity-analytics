"""
Yahoo Finance Data Fetcher

This module fetches stock fundamental data from Yahoo Finance using the yfinance library.
It provides a standardized data format that works with our guru strategies.
"""

import yfinance as yf
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def fetch_stock_data_yahoo(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Fetch stock fundamental data from Yahoo Finance.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        
    Returns:
        Dictionary with standardized stock data, or None if fetch fails
        
    Returns format:
        {
            'ticker': str,
            'current_price': float,
            'pe_ratio': float,
            'pb_ratio': float,
            'roe': float (as decimal, e.g., 0.30 = 30%),
            'net_margin': float (as decimal),
            'debt_to_equity': float,
            'earnings_growth': float (as decimal),
            'revenue_growth': float (as decimal),
            'dividend_yield': float (as decimal),
            'market_cap': float,
            'eps': float,
            'peg_ratio': float,
            'sector': str,
            'industry': str,
            'source': 'yahoo'
        }
        
    Example:
        >>> data = fetch_stock_data_yahoo('AAPL')
        >>> print(f"Price: ${data['current_price']:.2f}")
        Price: $150.00
    """
    try:
        logger.info(f"Fetching data for {ticker} from Yahoo Finance")
        
        # Create ticker object
        stock = yf.Ticker(ticker)
        
        # Fetch info
        info = stock.info
        
        # Check if we got valid data
        if not info or 'symbol' not in info:
            logger.warning(f"No data returned for {ticker}")
            return None
        
        # Extract and standardize data
        # Use .get() with defaults to handle missing data gracefully
        data = {
            'ticker': ticker.upper(),
            'current_price': info.get('currentPrice') or info.get('regularMarketPrice', 0.0),
            'pe_ratio': info.get('trailingPE') or info.get('forwardPE', 0.0),
            'pb_ratio': info.get('priceToBook', 0.0),
            'roe': info.get('returnOnEquity', 0.0),  # Already as decimal
            'net_margin': info.get('profitMargins', 0.0),  # Already as decimal
            'debt_to_equity': info.get('debtToEquity', 0.0) / 100.0 if info.get('debtToEquity') else 0.0,
            'earnings_growth': info.get('earningsGrowth', 0.0),  # Already as decimal
            'revenue_growth': info.get('revenueGrowth', 0.0),  # Already as decimal
            'dividend_yield': info.get('dividendYield', 0.0),  # Already as decimal
            'market_cap': info.get('marketCap', 0.0),
            'eps': info.get('trailingEps') or info.get('forwardEps', 0.0),
            'peg_ratio': info.get('pegRatio', 0.0),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            'source': 'yahoo'
        }
        
        # Validate that we have essential data
        if data['current_price'] == 0 or data['eps'] == 0:
            logger.warning(f"Missing essential data for {ticker}")
            return None
        
        logger.info(f"Successfully fetched {ticker} data from Yahoo Finance")
        return data
        
    except Exception as e:
        logger.error(f"Error fetching {ticker} from Yahoo Finance: {e}")
        return None


def fetch_stock_history(ticker: str, period: str = "1y") -> Optional[Dict[str, Any]]:
    """
    Fetch historical price data for a stock.
    
    Args:
        ticker: Stock ticker symbol
        period: Time period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max')
        
    Returns:
        Dictionary with historical data and calculated metrics
        
    Example:
        >>> history = fetch_stock_history('AAPL', '1y')
        >>> print(f"52-week high: ${history['high_52w']:.2f}")
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        
        if hist.empty:
            logger.warning(f"No historical data for {ticker}")
            return None
        
        # Calculate key metrics
        current_price = hist['Close'].iloc[-1]
        high_52w = hist['High'].max()
        low_52w = hist['Low'].min()
        avg_volume = hist['Volume'].mean()
        
        return {
            'ticker': ticker.upper(),
            'current_price': float(current_price),
            'high_52w': float(high_52w),
            'low_52w': float(low_52w),
            'avg_volume': float(avg_volume),
            'price_change_pct': float(((current_price - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100),
            'volatility': float(hist['Close'].pct_change().std() * 100),  # Daily volatility %
            'data_points': len(hist),
            'period': period,
            'source': 'yahoo'
        }
        
    except Exception as e:
        logger.error(f"Error fetching history for {ticker}: {e}")
        return None


def validate_ticker(ticker: str) -> bool:
    """
    Check if a ticker symbol is valid and tradable.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        True if ticker exists and has data, False otherwise
        
    Example:
        >>> validate_ticker('AAPL')
        True
        >>> validate_ticker('INVALID')
        False
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Check if we got valid data and it's a stock (not index, etc.)
        return bool(info and 'symbol' in info and info.get('quoteType') == 'EQUITY')
        
    except Exception as e:
        logger.error(f"Error validating ticker {ticker}: {e}")
        return False

