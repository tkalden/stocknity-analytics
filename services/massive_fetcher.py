"""
Entry point for sector fundamental data.
Delegates to the configured data source (STOCK_DATA_SOURCE env var).
chart.py and data_fetcher.py import fetch_sector_fundamentals from here — nothing else changes.
"""

from typing import List, Dict
from services.sources.base import FetchResult

# Static sector ticker lists — shared by all sources that need them
SECTOR_TICKERS: Dict[str, List[str]] = {
    "Technology": [
        "AAPL","MSFT","NVDA","META","AVGO","ORCL","CRM","AMD","QCOM","TXN",
    ],
    "Healthcare": [
        "UNH","LLY","JNJ","ABBV","MRK","TMO","ABT","DHR","BMY","AMGN",
    ],
    "Financial": [
        "JPM","V","MA","BAC","WFC","GS","MS","AXP","BLK","SCHW",
    ],
    "Consumer Cyclical": [
        "AMZN","TSLA","HD","MCD","NKE","LOW","SBUX","TGT","BKNG","CMG",
    ],
    "Consumer Defensive": [
        "WMT","PG","KO","PEP","COST","PM","MO","CL","KMB","GIS",
    ],
    "Energy": [
        "XOM","CVX","COP","EOG","SLB","KMI","WMB","OKE","HAL","DVN",
    ],
    "Industrials": [
        "CAT","RTX","HON","UPS","BA","DE","LMT","GE","MMM","ETN",
    ],
    "Basic Materials": [
        "LIN","APD","SHW","FCX","NEM","DOW","DD","PPG","NUE","CF",
    ],
    "Real Estate": [
        "PLD","AMT","EQIX","CCI","PSA","O","WELL","DLR","AVB","EQR",
    ],
    "Communication Services": [
        "GOOGL","META","NFLX","DIS","CMCSA","T","VZ","TMUS","CHTR","LYV",
    ],
    "Utilities": [
        "NEE","DUK","SO","AEP","SRE","XEL","ED","WEC","ES","FE",
    ],
}

# Add "Any" as all tickers combined (deduped)
SECTOR_TICKERS["Any"] = list(dict.fromkeys(
    t for tickers in SECTOR_TICKERS.values() for t in tickers
))


def fetch_sector_fundamentals(sector: str) -> FetchResult:
    """
    Fetch fundamental/performance data for all tickers in a sector.
    Source is determined by STOCK_DATA_SOURCE env var (fmp | massive | yfinance).
    """
    from services.sources import get_data_source
    return get_data_source().fetch_sector(sector)


def get_all_sector_tickers(sector: str) -> List[str]:
    return SECTOR_TICKERS.get(sector, [])
