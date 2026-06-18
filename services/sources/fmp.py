"""
FMP (Financial Modeling Prep) data source — Starter plan.
Per ticker: stable/profile (price, dividend, change) + stable/ratios-ttm (P/E, P/B, PEG).
annual_return filled from yfinance batch download (FMP has no 1-year return endpoint).
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
import requests
import pandas as pd
import yfinance as yf

from services.sources.base import StockDataSource, FetchResult
from services.massive_fetcher import SECTOR_TICKERS

logger = logging.getLogger(__name__)

FMP_BASE = "https://financialmodelingprep.com/stable"
_MAX_WORKERS = 10


class FMPDataSource(StockDataSource):

    def __init__(self):
        self.api_key = os.getenv("FMP_API_KEY", "")
        if not self.api_key:
            raise ValueError("FMP_API_KEY not set")
        self._session = requests.Session()

    @property
    def source_name(self) -> str:
        return "fmp"

    def fetch_sector(self, sector: str) -> FetchResult:
        try:
            tickers = SECTOR_TICKERS.get(sector, [])
            if not tickers:
                return FetchResult(success=False, data=pd.DataFrame(),
                                   source=self.source_name,
                                   error=f"Unknown sector: {sector}")

            # Batch yfinance for annual_return + dividend backup
            annual_returns = self._fetch_annual_returns(tickers)

            rows = self._fetch_all(tickers, annual_returns)
            if not rows:
                return FetchResult(success=False, data=pd.DataFrame(),
                                   source=self.source_name,
                                   error=f"All tickers failed for {sector}")

            df = pd.DataFrame(rows)
            logger.info("FMP fetched %d tickers for %s", len(df), sector)
            return FetchResult(success=True, data=df, source=self.source_name)

        except Exception as e:
            logger.error("FMP fetch error for %s: %s", sector, e)
            return FetchResult(success=False, data=pd.DataFrame(),
                               source=self.source_name, error=str(e))

    def _fetch_annual_returns(self, tickers: list) -> dict:
        """Bulk yfinance download for 1-year return per ticker."""
        try:
            raw = yf.download(
                tickers, period="1y", interval="1d",
                auto_adjust=True, actions=True,
                progress=False, threads=True
            )
            closes = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
            result = {}
            for t in tickers:
                try:
                    col = closes[t] if t in closes.columns else closes
                    col = col.dropna()
                    if len(col) >= 2:
                        ret = ((col.iloc[-1] - col.iloc[0]) / col.iloc[0]) * 100
                        result[t] = round(float(ret), 2)
                except Exception:
                    pass
            return result
        except Exception as e:
            logger.warning("yfinance annual_return batch failed: %s", e)
            return {}

    def _fetch_all(self, tickers, annual_returns):
        rows = []
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            futures = {pool.submit(self._fetch_ticker, t, annual_returns): t for t in tickers}
            for fut in as_completed(futures):
                row = fut.result()
                if row:
                    rows.append(row)
        return rows

    def _fetch_ticker(self, ticker: str, annual_returns: dict) -> Optional[dict]:
        try:
            profile = self._get(f"{FMP_BASE}/profile", {"symbol": ticker})
            if not profile:
                return None

            p = profile[0]
            price = float(p.get("price") or 0)
            last_div = float(p.get("lastDividend") or 0)
            div_yield = round(last_div / price, 4) if price > 0 else 0.0

            ratios = self._get_optional(f"{FMP_BASE}/ratios-ttm", {"symbol": ticker})
            r = ratios[0] if ratios else {}

            pe  = r.get("priceToEarningsRatioTTM")
            pb  = r.get("priceToBookRatioTTM")
            peg = r.get("priceToEarningsGrowthRatioTTM")
            fpe = r.get("priceEarningsToGrowthRatioTTM")  # FMP calls it PEGY sometimes

            return {
                "Ticker":        ticker,
                "pe":            float(pe)  if pe  is not None else None,
                "pb":            float(pb)  if pb  is not None else None,
                "fpe":           float(fpe) if fpe is not None else None,
                "peg":           float(peg) if peg is not None else None,
                "dividend":      div_yield,
                "annual_return": annual_returns.get(ticker),
                "today_change":  float(p.get("changePercentage") or 0),
                "price":         price,
            }
        except Exception as e:
            logger.warning("FMP ticker %s failed: %s", ticker, e)
            return None

    def _get(self, url: str, extra_params: dict) -> list:
        params = {"apikey": self.api_key, **extra_params}
        r = self._session.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []

    def _get_optional(self, url: str, extra_params: dict) -> list:
        try:
            return self._get(url, extra_params)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 402:
                return []
            raise
