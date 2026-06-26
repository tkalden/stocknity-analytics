"""
Writes current prices for Alpaca-subscribed tickers to Redis every 15 min.
Java RedisFallbackPoller reads prices:* when Alpaca WebSocket is down.
"""

import logging
import threading
import time
from datetime import datetime

import yfinance as yf

logger = logging.getLogger(__name__)

TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "TSLA",
    "BRK-B", "AVGO", "LLY", "JPM", "UNH", "V", "XOM", "MA", "COST",
    "HD", "PG", "JNJ", "ABBV", "WMT", "BAC", "MRK", "ORCL", "CVX",
    "CRM", "KO", "AMD", "NFLX",
]

REFRESH_INTERVAL = 15 * 60  # 15 minutes
REDIS_TTL = 20 * 60         # 20 minutes — expires if refresh stops


def refresh_prices(r) -> int:
    try:
        data = yf.download(
            TICKERS, period="1d", interval="1m",
            auto_adjust=True, progress=False, threads=True
        )
        closes = data["Close"] if hasattr(data.columns, "levels") else data
        count = 0
        pipe = r.pipeline()
        for ticker in TICKERS:
            try:
                col = closes[ticker] if ticker in closes.columns else None
                if col is None:
                    continue
                col = col.dropna()
                if col.empty:
                    continue
                price = round(float(col.iloc[-1]), 4)
                if price <= 0:
                    continue
                pipe.setex(f"prices:{ticker}", REDIS_TTL, str(price))
                count += 1
            except Exception as e:
                logger.debug("price_cache skip %s: %s", ticker, e)
        pipe.execute()
        logger.info("price_cache: wrote %d prices to Redis", count)
        return count
    except Exception as e:
        logger.error("price_cache refresh failed: %s", e)
        return 0


def run_price_cache(r):
    logger.info("price_cache: starting (refresh every %d min)", REFRESH_INTERVAL // 60)
    while True:
        refresh_prices(r)
        time.sleep(REFRESH_INTERVAL)


def start_price_cache(r):
    t = threading.Thread(target=run_price_cache, args=(r,), daemon=True)
    t.start()
    return t
