"""
Massive (Polygon.io) + yfinance data source.
- Polygon batch snapshot → today's change, price
- yfinance download     → 1-year annual return (batch, no rate limits)
- yfinance fast_info    → dividend yield (lightweight)
No P/E/P/B (requires Polygon paid tier).
"""

import logging
import os
from typing import Dict, List, Tuple
import requests
import yfinance as yf
import pandas as pd

from services.sources.base import StockDataSource, FetchResult
from services.massive_fetcher import SECTOR_TICKERS   # reuse static ticker map

logger = logging.getLogger(__name__)

POLYGON_SNAPSHOT = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers"


class MassiveDataSource(StockDataSource):

    def __init__(self):
        self.api_key = os.getenv("POLYGON_API_KEY", "")

    @property
    def source_name(self) -> str:
        return "massive"

    def fetch_sector(self, sector: str) -> FetchResult:
        tickers = SECTOR_TICKERS.get(sector, [])
        if not tickers:
            return FetchResult(success=False, data=pd.DataFrame(),
                               source=self.source_name,
                               error=f"Unknown sector: {sector}")

        snapshots = self._snapshot(tickers)
        returns, dividends = self._annual_returns_and_dividends(tickers)

        rows = []
        for t in tickers:
            snap = snapshots.get(t, {})
            day = snap.get("day", {})
            prev = snap.get("prevDay", {})
            price = day.get("c") or prev.get("c") or 0

            rows.append({
                "Ticker":        t,
                "pe":            None,
                "pb":            None,
                "fpe":           None,
                "peg":           None,
                "dividend":      dividends.get(t, 0.0),
                "annual_return": returns.get(t, 0.0),
                "today_change":  snap.get("todaysChangePerc", 0.0) or 0.0,
                "price":         float(price),
            })

        df = pd.DataFrame(rows)
        logger.info("Massive fetched %d tickers for %s", len(df), sector)
        return FetchResult(success=True, data=df, source=self.source_name)

    def _snapshot(self, tickers: List[str]) -> Dict[str, dict]:
        if not self.api_key:
            return {}
        try:
            r = requests.get(POLYGON_SNAPSHOT,
                             params={"tickers": ",".join(tickers), "apiKey": self.api_key},
                             timeout=10)
            r.raise_for_status()
            return {item["ticker"]: item for item in r.json().get("tickers", [])}
        except Exception as e:
            logger.warning("Polygon snapshot failed: %s", e)
            return {}

    def _annual_returns_and_dividends(self, tickers: List[str]):
        """Single batch download for returns + dividends."""
        returns, dividends = {}, {}
        try:
            df = yf.download(tickers, period="1y", progress=False,
                             auto_adjust=True, actions=True)
            if df.empty:
                return returns, dividends
            close = df["Close"]
            div_df = df.get("Dividends", pd.DataFrame())
            for t in tickers:
                try:
                    col = close[t].dropna()
                    if len(col) < 2:
                        continue
                    price = float(col.iloc[-1])
                    returns[t] = round(((col.iloc[-1] - col.iloc[0]) / col.iloc[0]) * 100, 2)
                    if not div_df.empty and t in div_df.columns:
                        annual_div = float(div_df[t].sum())
                        dividends[t] = round(annual_div / price, 4) if price > 0 else 0.0
                    else:
                        dividends[t] = 0.0
                except Exception:
                    pass
        except Exception as e:
            logger.warning("yf.download failed: %s", e)
        return returns, dividends
