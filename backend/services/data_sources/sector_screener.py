"""
Sector-Based Stock Screener

Yahoo Finance doesn't provide a direct "get all stocks in sector" API,
so we maintain common sector mappings and provide screening utilities.
"""

from typing import Dict, List, Set
import logging

logger = logging.getLogger(__name__)


# S&P 500 stocks by sector (curated list - update periodically)
# This is a subset; full list would have ~500 stocks
SP500_BY_SECTOR: Dict[str, List[str]] = {
    'Technology': [
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'NVDA', 'META', 'TSLA', 'AVGO',
        'ORCL', 'ADBE', 'CRM', 'ACN', 'CSCO', 'AMD', 'INTC', 'IBM',
        'INTU', 'TXN', 'QCOM', 'AMAT', 'ADI', 'MU', 'LRCX', 'KLAC',
        'SNPS', 'CDNS', 'MCHP', 'FTNT', 'ANSS', 'ON'
    ],
    'Healthcare': [
        'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR',
        'PFE', 'BMY', 'AMGN', 'CVS', 'ELV', 'CI', 'MDT', 'GILD',
        'ISRG', 'REGN', 'VRTX', 'ZTS', 'BSX', 'HUM', 'SYK', 'MCK'
    ],
    'Financial Services': [
        'BRK.B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'MS', 'GS',
        'SPGI', 'BLK', 'C', 'AXP', 'SCHW', 'CB', 'MMC', 'PGR',
        'BK', 'AON', 'USB', 'TFC', 'COF', 'AIG', 'MET', 'PRU'
    ],
    'Consumer Cyclical': [
        'AMZN', 'TSLA', 'HD', 'NKE', 'MCD', 'LOW', 'SBUX', 'TGT',
        'BKNG', 'ABNB', 'CMG', 'MAR', 'GM', 'F', 'ROST', 'YUM',
        'DHI', 'LEN', 'HLT', 'DG', 'ORLY', 'APTV', 'POOL', 'BBY'
    ],
    'Consumer Defensive': [
        'WMT', 'PG', 'KO', 'PEP', 'COST', 'PM', 'MO', 'CL',
        'MDLZ', 'KMB', 'GIS', 'KHC', 'SYY', 'HSY', 'K', 'CPB',
        'CAG', 'CHD', 'CLX', 'TSN', 'HRL', 'MKC', 'SJM', 'LW'
    ],
    'Energy': [
        'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO',
        'OXY', 'WMB', 'KMI', 'HAL', 'DVN', 'HES', 'FANG', 'BKR',
        'EQT', 'TRGP', 'MRO', 'APA', 'CTRA', 'OKE', 'CQP', 'LNG'
    ],
    'Industrials': [
        'UPS', 'HON', 'UNP', 'RTX', 'BA', 'CAT', 'DE', 'LMT',
        'GE', 'MMM', 'GD', 'NOC', 'ETN', 'ITW', 'PH', 'EMR',
        'CARR', 'NSC', 'FDX', 'CSX', 'WM', 'RSG', 'PCAR', 'CMI'
    ],
    'Communication Services': [
        'GOOGL', 'GOOG', 'META', 'DIS', 'NFLX', 'CMCSA', 'VZ',
        'T', 'TMUS', 'CHTR', 'EA', 'ATVI', 'TTWO', 'LYV', 'PARA',
        'WBD', 'MTCH', 'FOXA', 'FOX', 'OMC', 'IPG', 'NWSA', 'NWS'
    ],
    'Real Estate': [
        'AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'WELL', 'DLR', 'O',
        'SPG', 'SBAC', 'AVB', 'EQR', 'VICI', 'WY', 'VTR', 'ARE',
        'INVH', 'MAA', 'ESS', 'UDR', 'CPT', 'HST', 'REG', 'BXP'
    ],
    'Utilities': [
        'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'PEG',
        'XEL', 'ED', 'EIX', 'WEC', 'ES', 'AWK', 'DTE', 'PPL',
        'FE', 'AEE', 'CMS', 'CNP', 'ETR', 'ATO', 'NI', 'LNT'
    ],
    'Basic Materials': [
        'LIN', 'APD', 'ECL', 'SHW', 'DD', 'NEM', 'FCX', 'CTVA',
        'DOW', 'NUE', 'VMC', 'MLM', 'PPG', 'IFF', 'ALB', 'EMN',
        'MOS', 'FMC', 'CE', 'CF', 'STLD', 'IP', 'PKG', 'AMCR'
    ]
}

# Reverse mapping: ticker -> sector
TICKER_TO_SECTOR: Dict[str, str] = {}
for sector, tickers in SP500_BY_SECTOR.items():
    for ticker in tickers:
        TICKER_TO_SECTOR[ticker] = sector


def get_tickers_by_sector(sector: str) -> List[str]:
    """
    Get list of ticker symbols for a given sector.
    
    Args:
        sector: Sector name (e.g., 'Technology', 'Healthcare')
        
    Returns:
        List of ticker symbols in that sector
        
    Example:
        >>> tech_stocks = get_tickers_by_sector('Technology')
        >>> print(f"Found {len(tech_stocks)} tech stocks")
        Found 30 tech stocks
    """
    return SP500_BY_SECTOR.get(sector, [])


def get_sector_for_ticker(ticker: str) -> str:
    """
    Get the sector for a given ticker symbol.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Sector name or 'Unknown'
        
    Example:
        >>> sector = get_sector_for_ticker('AAPL')
        >>> print(f"AAPL is in {sector}")
        AAPL is in Technology
    """
    return TICKER_TO_SECTOR.get(ticker.upper(), 'Unknown')


def get_all_sectors() -> List[str]:
    """
    Get list of all available sectors.
    
    Returns:
        List of sector names
    """
    return list(SP500_BY_SECTOR.keys())


def filter_tickers_by_sectors(tickers: List[str], sectors: List[str]) -> List[str]:
    """
    Filter a list of tickers to only include those in specified sectors.
    
    Args:
        tickers: List of ticker symbols to filter
        sectors: List of sectors to include
        
    Returns:
        Filtered list of tickers
        
    Example:
        >>> all_tickers = ['AAPL', 'JPM', 'MSFT', 'BAC']
        >>> tech_only = filter_tickers_by_sectors(all_tickers, ['Technology'])
        >>> print(tech_only)
        ['AAPL', 'MSFT']
    """
    sector_set = set(sectors)
    return [
        ticker for ticker in tickers
        if get_sector_for_ticker(ticker) in sector_set
    ]


def get_sector_diversification(tickers: List[str]) -> Dict[str, int]:
    """
    Analyze sector diversification of a portfolio.
    
    Args:
        tickers: List of ticker symbols
        
    Returns:
        Dictionary mapping sector -> count of stocks
        
    Example:
        >>> portfolio = ['AAPL', 'MSFT', 'JPM', 'BAC', 'GOOGL']
        >>> diversification = get_sector_diversification(portfolio)
        >>> print(diversification)
        {'Technology': 3, 'Financial Services': 2}
    """
    diversification: Dict[str, int] = {}
    
    for ticker in tickers:
        sector = get_sector_for_ticker(ticker)
        diversification[sector] = diversification.get(sector, 0) + 1
    
    return diversification


def get_popular_stocks_by_sector(sector: str, limit: int = 10) -> List[str]:
    """
    Get the most popular (liquid, large-cap) stocks in a sector.
    
    Returns the first N stocks from our curated list, which are ordered
    roughly by market cap / popularity.
    
    Args:
        sector: Sector name
        limit: Maximum number of stocks to return
        
    Returns:
        List of ticker symbols
        
    Example:
        >>> top_tech = get_popular_stocks_by_sector('Technology', 5)
        >>> print(top_tech)
        ['AAPL', 'MSFT', 'GOOGL', 'GOOG', 'NVDA']
    """
    all_tickers = get_tickers_by_sector(sector)
    return all_tickers[:limit]


# Sector descriptions for educational purposes
SECTOR_DESCRIPTIONS = {
    'Technology': 'Companies that develop, produce, or distribute technology products and services, including software, hardware, and IT services.',
    'Healthcare': 'Companies involved in medical services, pharmaceuticals, biotechnology, and healthcare equipment.',
    'Financial Services': 'Banks, investment firms, insurance companies, and other financial service providers.',
    'Consumer Cyclical': 'Companies selling non-essential goods and services that are sensitive to economic cycles (retail, automotive, restaurants).',
    'Consumer Defensive': 'Companies selling essential products that remain in demand regardless of economic conditions (food, beverages, household goods).',
    'Energy': 'Companies involved in oil, gas, coal production, and renewable energy.',
    'Industrials': 'Manufacturing, aerospace, defense, construction, and transportation companies.',
    'Communication Services': 'Telecommunications, media, entertainment, and internet service providers.',
    'Real Estate': 'Real estate investment trusts (REITs) and real estate management companies.',
    'Utilities': 'Electric, gas, water utilities and renewable energy producers.',
    'Basic Materials': 'Companies producing raw materials including chemicals, metals, mining, and forestry products.'
}


def get_sector_description(sector: str) -> str:
    """
    Get educational description of a sector.
    
    Args:
        sector: Sector name
        
    Returns:
        Description text
    """
    return SECTOR_DESCRIPTIONS.get(sector, 'No description available.')

