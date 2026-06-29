#!/usr/bin/env python3
"""
Stocknity - Advanced Stock Portfolio Management System

This Flask service is read-only analytics. It does NOT refresh, write, or
delete cache. The stocknity-market-data service (ScreenerDataAggregator)
owns population of the canonical stock_data:* Redis keys.
"""

import os
import sys
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from core.app import app

logger = logging.getLogger(__name__)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)
