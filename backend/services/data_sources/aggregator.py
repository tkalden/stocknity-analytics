"""
Stock Data Aggregator with Multi-Source Fallback

This module provides intelligent data aggregation from multiple sources with:
- Redis caching (1-hour TTL)
- Rate limiting (10 calls/minute per source)
- Automatic fallback when sources fail
- Comprehensive logging

Architecture:
1. Check Redis cache first
2. Try Yahoo Finance
3. (Future: Try Alpha Vantage, FMP as fallbacks)
4. Return cached data if all sources fail
"""

import os
import json
import logging
import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Try to import Redis, fall back to dict cache if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available, using in-memory cache")

from backend.services.data_sources.yahoo_finance import fetch_stock_data_yahoo

logger = logging.getLogger(__name__)


class DataAggregator:
    """
    Intelligent stock data aggregator with caching and fallback.
    
    Features:
    - Multi-source data fetching with prioritization
    - Redis caching with 1-hour TTL
    - Rate limiting (10 calls/minute per source)
    - Automatic fallback to cached data
    - Comprehensive logging
    
    Example:
        >>> aggregator = DataAggregator()
        >>> data = await aggregator.fetch_stock('AAPL')
        >>> print(f"Price: ${data['current_price']}")
        Price: $150.00
    """
    
    # Configuration
    CACHE_TTL = 3600  # 1 hour in seconds
    RATE_LIMIT_WINDOW = 60  # 1 minute in seconds
    RATE_LIMIT_MAX_CALLS = 10  # Max calls per window
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the data aggregator.
        
        Args:
            redis_url: Redis connection URL (optional, will try env var if not provided)
        """
        self.redis_url = redis_url or os.getenv('REDIS_URL')
        self.redis_client = None
        self.memory_cache: Dict[str, Dict] = {}  # Fallback in-memory cache
        self.rate_limit_tracker: Dict[str, list] = defaultdict(list)  # Track API calls
        
        # Try to connect to Redis
        if REDIS_AVAILABLE and self.redis_url:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                # Test connection
                self.redis_client.ping()
                logger.info("✅ Connected to Redis cache")
            except Exception as e:
                logger.warning(f"⚠️ Could not connect to Redis: {e}. Using memory cache.")
                self.redis_client = None
        else:
            logger.info("Using in-memory cache (Redis not configured)")
    
    async def fetch_stock(self, ticker: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetch stock data with intelligent caching and fallback.
        
        Strategy:
        1. Check cache (unless force_refresh=True)
        2. Try Yahoo Finance
        3. (Future) Try other sources
        4. Return stale cache if all fail
        
        Args:
            ticker: Stock ticker symbol
            force_refresh: Skip cache and fetch fresh data
            
        Returns:
            Stock data dictionary or None if all sources fail
            
        Example:
            >>> data = await aggregator.fetch_stock('AAPL')
            >>> if data:
            ...     print(f"Fetched from: {data['source']}")
        """
        ticker = ticker.upper()
        cache_key = f"stock:{ticker}"
        
        # Step 1: Check cache (unless force refresh)
        if not force_refresh:
            cached_data = self._get_from_cache(cache_key)
            if cached_data:
                logger.info(f"✅ Cache hit for {ticker}")
                cached_data['cached'] = True
                cached_data['cache_time'] = cached_data.get('fetched_at', 'unknown')
                return cached_data
        
        # Step 2: Try Yahoo Finance
        if self._check_rate_limit('yahoo'):
            data = fetch_stock_data_yahoo(ticker)
            if data:
                data['fetched_at'] = datetime.now().isoformat()
                data['cached'] = False
                self._save_to_cache(cache_key, data)
                self._record_api_call('yahoo')
                logger.info(f"✅ Fetched {ticker} from Yahoo Finance")
                return data
            else:
                logger.warning(f"⚠️ Yahoo Finance failed for {ticker}")
        else:
            logger.warning(f"⚠️ Rate limit exceeded for Yahoo Finance")
        
        # Step 3: (Future) Try other sources like Alpha Vantage, FMP
        # TODO: Add more data sources
        
        # Step 4: Return stale cache as last resort
        stale_data = self._get_from_cache(cache_key, allow_stale=True)
        if stale_data:
            logger.warning(f"⚠️ Returning stale cache for {ticker}")
            stale_data['cached'] = True
            stale_data['stale'] = True
            return stale_data
        
        # All sources failed and no cache available
        logger.error(f"❌ All sources failed for {ticker} and no cache available")
        return None
    
    async def fetch_stocks_batch(
        self, 
        tickers: List[str], 
        max_workers: int = 10,
        force_refresh: bool = False
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Fetch multiple stocks concurrently for much faster performance.
        
        This method fetches stocks in parallel using ThreadPoolExecutor,
        making it ~10x faster than sequential fetching.
        
        Args:
            tickers: List of ticker symbols to fetch
            max_workers: Maximum concurrent requests (default: 10)
            force_refresh: Skip cache and fetch fresh data
            
        Returns:
            Dictionary mapping ticker -> stock data (or None if failed)
            
        Example:
            >>> aggregator = DataAggregator()
            >>> results = await aggregator.fetch_stocks_batch(['AAPL', 'MSFT', 'GOOGL'])
            >>> for ticker, data in results.items():
            ...     if data:
            ...         print(f"{ticker}: ${data['current_price']:.2f}")
            AAPL: $150.00
            MSFT: $300.00
            GOOGL: $120.00
        """
        logger.info(f"📦 Batch fetching {len(tickers)} stocks with {max_workers} workers")
        start_time = time.time()
        
        results = {}
        
        # Use ThreadPoolExecutor for concurrent fetching
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all fetch tasks
            future_to_ticker = {
                loop.run_in_executor(
                    executor,
                    self._fetch_stock_sync,
                    ticker,
                    force_refresh
                ): ticker
                for ticker in tickers
            }
            
            # Gather results as they complete
            completed = 0
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    data = await future
                    results[ticker] = data
                    completed += 1
                    if completed % 10 == 0:
                        logger.info(f"Progress: {completed}/{len(tickers)} stocks fetched")
                except Exception as e:
                    logger.error(f"Error fetching {ticker} in batch: {e}")
                    results[ticker] = None
        
        elapsed = time.time() - start_time
        success_count = sum(1 for data in results.values() if data is not None)
        
        logger.info(
            f"✅ Batch complete: {success_count}/{len(tickers)} succeeded in {elapsed:.2f}s "
            f"({len(tickers)/elapsed:.1f} stocks/sec)"
        )
        
        return results
    
    def _fetch_stock_sync(self, ticker: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Synchronous wrapper for fetch_stock (used by ThreadPoolExecutor).
        
        Args:
            ticker: Stock ticker symbol
            force_refresh: Skip cache
            
        Returns:
            Stock data or None
        """
        # Run the async method in a sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.fetch_stock(ticker, force_refresh))
        finally:
            loop.close()
    
    def _get_from_cache(self, key: str, allow_stale: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get data from Redis or memory cache.
        
        Args:
            key: Cache key
            allow_stale: If True, return expired data
            
        Returns:
            Cached data or None
        """
        try:
            # Try Redis first
            if self.redis_client:
                cached = self.redis_client.get(key)
                if cached:
                    return json.loads(cached)
                
                # Check for stale data if allowed
                if allow_stale:
                    stale_key = f"{key}:stale"
                    stale_cached = self.redis_client.get(stale_key)
                    if stale_cached:
                        return json.loads(stale_cached)
            
            # Fallback to memory cache
            if key in self.memory_cache:
                cache_entry = self.memory_cache[key]
                if allow_stale or cache_entry.get('expires_at', 0) > time.time():
                    return cache_entry.get('data')
            
            return None
            
        except Exception as e:
            logger.error(f"Error reading from cache: {e}")
            return None
    
    def _save_to_cache(self, key: str, data: Dict[str, Any]) -> bool:
        """
        Save data to Redis and memory cache.
        
        Args:
            key: Cache key
            data: Data to cache
            
        Returns:
            True if saved successfully
        """
        try:
            data_json = json.dumps(data)
            
            # Save to Redis
            if self.redis_client:
                # Save with TTL
                self.redis_client.setex(key, self.CACHE_TTL, data_json)
                
                # Also save to stale backup (longer TTL)
                stale_key = f"{key}:stale"
                self.redis_client.setex(stale_key, self.CACHE_TTL * 24, data_json)  # 24 hours
                
                logger.debug(f"Saved {key} to Redis cache")
            
            # Save to memory cache as backup
            self.memory_cache[key] = {
                'data': data,
                'expires_at': time.time() + self.CACHE_TTL
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")
            return False
    
    def _check_rate_limit(self, source: str) -> bool:
        """
        Check if we can make an API call to the source without exceeding rate limit.
        
        Rate limit: 10 calls per minute per source
        
        Args:
            source: Data source name (e.g., 'yahoo', 'alpha_vantage')
            
        Returns:
            True if we can make a call, False if rate limited
        """
        current_time = time.time()
        window_start = current_time - self.RATE_LIMIT_WINDOW
        
        # Get calls in current window
        calls = self.rate_limit_tracker[source]
        
        # Remove old calls outside the window
        calls = [call_time for call_time in calls if call_time > window_start]
        self.rate_limit_tracker[source] = calls
        
        # Check if we're under the limit
        return len(calls) < self.RATE_LIMIT_MAX_CALLS
    
    def _record_api_call(self, source: str) -> None:
        """
        Record an API call for rate limiting.
        
        Args:
            source: Data source name
        """
        self.rate_limit_tracker[source].append(time.time())
    
    def clear_cache(self, ticker: Optional[str] = None) -> bool:
        """
        Clear cache for a specific ticker or all tickers.
        
        Args:
            ticker: Ticker to clear (None = clear all)
            
        Returns:
            True if cleared successfully
        """
        try:
            if ticker:
                key = f"stock:{ticker.upper()}"
                if self.redis_client:
                    self.redis_client.delete(key)
                    self.redis_client.delete(f"{key}:stale")
                if key in self.memory_cache:
                    del self.memory_cache[key]
                logger.info(f"Cleared cache for {ticker}")
            else:
                if self.redis_client:
                    # Clear all stock keys
                    for key in self.redis_client.scan_iter("stock:*"):
                        self.redis_client.delete(key)
                self.memory_cache.clear()
                logger.info("Cleared all cache")
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        stats = {
            'redis_connected': self.redis_client is not None,
            'memory_cache_size': len(self.memory_cache),
            'rate_limits': {}
        }
        
        # Add rate limit info
        for source, calls in self.rate_limit_tracker.items():
            current_time = time.time()
            window_start = current_time - self.RATE_LIMIT_WINDOW
            recent_calls = [c for c in calls if c > window_start]
            stats['rate_limits'][source] = {
                'calls_in_window': len(recent_calls),
                'limit': self.RATE_LIMIT_MAX_CALLS,
                'window_seconds': self.RATE_LIMIT_WINDOW
            }
        
        # Add Redis stats if available
        if self.redis_client:
            try:
                info = self.redis_client.info('stats')
                stats['redis_stats'] = {
                    'total_commands': info.get('total_commands_processed', 0),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0)
                }
                
                # Calculate hit rate
                hits = stats['redis_stats']['keyspace_hits']
                misses = stats['redis_stats']['keyspace_misses']
                if hits + misses > 0:
                    stats['redis_stats']['hit_rate'] = f"{(hits / (hits + misses)) * 100:.1f}%"
            except Exception as e:
                logger.error(f"Error getting Redis stats: {e}")
        
        return stats

