from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class FetchResult:
    success: bool
    data: pd.DataFrame
    source: str
    error: Optional[str] = None


class StockDataSource(ABC):
    """
    Implement this to add a new data source.
    fetch_sector() must return a DataFrame with these columns
    (missing columns → None, callers handle gracefully):

    Ticker          str   — ticker symbol
    pe              float — trailing P/E ratio
    pb              float — price-to-book ratio
    fpe             float — forward P/E ratio
    peg             float — PEG ratio
    dividend        float — annual dividend yield (decimal: 0.02 = 2%)
    annual_return   float — 1-year price return %
    today_change    float — today's % change
    price           float — current price
    """

    @abstractmethod
    def fetch_sector(self, sector: str) -> FetchResult:
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        pass
