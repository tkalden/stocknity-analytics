"""
Pure yfinance data source. No API key required.
Provides: annual_return, dividend_yield, today_change, price.
Single batch download covers price history, dividends, and today's change.
"""

import logging
from typing import Dict, List, Tuple
import yfinance as yf
import pandas as pd

from services.sources.base import StockDataSource, FetchResult
from services.massive_fetcher import SECTOR_TICKERS

logger = logging.getLogger(__name__)


class YFinanceDataSource(StockDataSource):

    @property
    def source_name(self) -> str:
        return "yfinance"

    def fetch_sector(self, sector: str) -> FetchResult:
        tickers = SECTOR_TICKERS.get(sector, [])
        if not tickers:
            return FetchResult(success=False, data=pd.DataFrame(),
                               source=self.source_name,
                               error=f"Unknown sector: {sector}")

        returns, dividends, prices, today_changes = self._batch_fetch(tickers)

        rows = [{
            "Ticker":        t,
            "pe":            None,
            "pb":            None,
            "fpe":           None,
            "peg":           None,
            "dividend":      dividends.get(t, 0.0),
            "annual_return": returns.get(t, 0.0),
            "today_change":  today_changes.get(t, 0.0),
            "price":         prices.get(t, 0.0),
        } for t in tickers]

        df = pd.DataFrame(rows)
        logger.info("yfinance fetched %d tickers for %s", len(df), sector)
        return FetchResult(success=True, data=df, source=self.source_name)

    def _batch_fetch(self, tickers: List[str]) -> Tuple[Dict, Dict, Dict, Dict]:
        """Single download call returns price history + dividends."""
        returns, dividends, prices, today_changes = {}, {}, {}, {}
        try:
            df = yf.download(tickers, period="1y", progress=False,
                             auto_adjust=True, actions=True)
            if df.empty:
                return returns, dividends, prices, today_changes

            close = df["Close"]
            div_df = df.get("Dividends", pd.DataFrame())

            for t in tickers:
                try:
                    col = close[t].dropna()
                    if len(col) < 2:
                        continue
                    price = float(col.iloc[-1])
                    prices[t] = round(price, 2)
                    returns[t] = round(((col.iloc[-1] - col.iloc[0]) / col.iloc[0]) * 100, 2)
                    today_changes[t] = round(((col.iloc[-1] - col.iloc[-2]) / col.iloc[-2]) * 100, 2) if len(col) >= 2 else 0.0

                    if not div_df.empty and t in div_df.columns:
                        annual_div = float(div_df[t].sum())
                        dividends[t] = round(annual_div / price, 4) if price > 0 else 0.0
                    else:
                        dividends[t] = 0.0
                except Exception:
                    pass

        except Exception as e:
            logger.warning("yf.download failed: %s", e)

        return returns, dividends, prices, today_changes
