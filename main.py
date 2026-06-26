#!/usr/bin/env python3
"""
Stocknity - Advanced Stock Portfolio Management System
"""

import os
import sys
import threading
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from core.app import app

logger = logging.getLogger(__name__)


def is_market_hours() -> bool:
    """True during NYSE market hours Mon-Fri 9:30-16:00 ET."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("America/New_York"))
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 570 <= minutes < 960  # 9:30 AM – 4:00 PM


def refresh_screener_cache():
    """
    Zero-downtime refresh: recompute all sector strength data in background,
    then atomically replace old cache entries. Users never hit a cold cache.
    """
    try:
        from utilities.redis_data import redis_manager
        from services.strengthCalculator import StrengthCalculator
        from utilities.constant import SECTORS

        sc = StrengthCalculator()
        r = redis_manager.r
        refreshed = 0

        for stock_type in ["Value", "Growth", "Dividend"]:
            for sector in ["Any"] + list(SECTORS):
                try:
                    # Compute fresh data (old cache still live during this)
                    df = sc.calculate_strength_value(
                        stock_type=stock_type,
                        sector=sector,
                        index="S&P 500"
                    )
                    if df is not None and not df.empty:
                        refreshed += 1
                except Exception as e:
                    logger.warning("Refresh failed %s/%s: %s", stock_type, sector, e)

        # Also flush chart_data so it recomputes on next chart request
        chart_keys = r.keys("chart_data:*") or []
        if chart_keys:
            r.delete(*chart_keys)

        logger.info("Screener refresh complete: %d combinations updated", refreshed)

    except Exception as e:
        logger.error("Screener refresh error: %s", e)


def run_refresh_scheduler():
    """Background thread: refresh screener cache every 30 min during market hours."""
    logger.info("Screener refresh scheduler started (30 min, market hours only)")
    while True:
        time.sleep(30 * 60)
        if is_market_hours():
            logger.info("Market open — refreshing screener cache")
            refresh_screener_cache()
        else:
            logger.info("Market closed — skipping refresh")


if __name__ == '__main__':
    t = threading.Thread(target=run_refresh_scheduler, daemon=True)
    t.start()

    from utilities.redis_data import redis_manager
    from services.price_cache import start_price_cache
    start_price_cache(redis_manager.r)

    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)
