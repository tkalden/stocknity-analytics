"""
Advanced Data Fetcher Service
Handles multiple data sources with fallbacks, async processing, and robust error handling
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import aiohttp
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
import yfinance as yf
from finvizfinance.screener.financial import Financial
from finvizfinance.screener.valuation import Valuation
from finvizfinance.screener.technical import Technical
from finvizfinance.screener.ownership import Ownership
from finvizfinance.screener.performance import Performance
from utilities.redis_data import redis_manager
from utilities.constant import SECTORS, INDEX, METRIC_COLUMNS, METRIC_SCHEMA

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataSource(Enum):
    FINVIZ = "finviz"
    YAHOO_FINANCE = "yahoo"
    ALPHA_VANTAGE = "alpha_vantage"
    POLYGON = "polygon"

@dataclass
class DataFetchResult:
    success: bool
    data: pd.DataFrame
    source: DataSource
    error: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class RateLimiter:
    """Smart rate limiter for API calls with exponential backoff"""
    
    def __init__(self, calls_per_second: int = 1):  # Reduced to 1 call per second
        self.calls_per_second = calls_per_second
        self.last_call = 0
        self.lock = asyncio.Lock()
        self.consecutive_errors = 0
        self.backoff_multiplier = 1
    
    async def wait(self):
        async with self.lock:
            now = time.time()
            time_since_last = now - self.last_call
            
            # Calculate wait time with exponential backoff
            base_wait = 1.0 / self.calls_per_second
            backoff_wait = base_wait * self.backoff_multiplier
            
            if time_since_last < backoff_wait:
                await asyncio.sleep(backoff_wait - time_since_last)
            
            self.last_call = time.time()
    
    def on_error(self, error_code: int = None):
        """Handle rate limiting errors with exponential backoff"""
        if error_code == 429:  # Rate limit exceeded
            self.consecutive_errors += 1
            self.backoff_multiplier = min(2 ** self.consecutive_errors, 60)  # Max 60 seconds
            logger.warning(f"Rate limit hit, backing off for {self.backoff_multiplier} seconds")
        else:
            # Reset backoff on successful calls
            self.consecutive_errors = 0
            self.backoff_multiplier = 1

class DataFetcher:
    """Advanced data fetcher with multiple sources and fallbacks"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(calls_per_second=1)  # Conservative rate limiting
        self.session = None
        self.finviz_services = {
            'valuation': Valuation(),
            'financial': Financial(),
            'technical': Technical(),
            'ownership': Ownership(),
            'performance': Performance()
        }
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Mozilla/5.0 (compatible; Stocknity/1.0)'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_stock_data(self, index: str, sector: str = 'Any') -> DataFetchResult:
        """Fetch stock data with multiple source fallbacks"""
        
        # Try Redis cache first
        cached_data = redis_manager.get_stock_data(index, sector)
        if not cached_data.empty:
            logger.info(f"Retrieved cached data for {index}:{sector}")
            return DataFetchResult(
                success=True,
                data=cached_data,
                source=DataSource.FINVIZ
            )
        
        # Try different data sources
        sources = [
            (self._fetch_from_finviz, DataSource.FINVIZ),
            (self._fetch_from_yahoo, DataSource.YAHOO_FINANCE),
        ]
        
        for fetch_func, source in sources:
            try:
                await self.rate_limiter.wait()
                result = await fetch_func(index, sector)
                if result.success and not result.data.empty:
                    # Cache the successful result
                    self._cache_data(result.data, index, sector)
                    return result
            except Exception as e:
                logger.warning(f"Failed to fetch from {source.value}: {e}")
                continue
        
        return DataFetchResult(
            success=False,
            data=pd.DataFrame(),
            source=DataSource.FINVIZ,
            error="All data sources failed"
        )
    
    async def _fetch_from_finviz(self, index: str, sector: str) -> DataFetchResult:
        """Fetch data from Finviz with improved error handling"""
        try:
            all_data = []
            
            for service_name, service in self.finviz_services.items():
                try:
                    await self.rate_limiter.wait()
                    
                    # Set filters
                    filters = {}
                    if sector != 'Any':
                        filters["Sector"] = sector
                    if index != 'Any':
                        filters["Index"] = index
                    
                    if filters:
                        service.set_filter(filters_dict=filters)
                    
                    data = service.screener_view()
                    if data is not None and not data.empty:
                        all_data.append(data)
                        logger.debug(f"Successfully fetched {service_name} data")
                    
                except Exception as e:
                    logger.warning(f"Error fetching {service_name} data: {e}")
                    continue
            
            if not all_data:
                return DataFetchResult(
                    success=False,
                    data=pd.DataFrame(),
                    source=DataSource.FINVIZ,
                    error="No data returned from Finviz"
                )
            
            # Combine and clean data
            combined_data = pd.concat(all_data, axis=1)
            cleaned_data = self._clean_and_validate_data(combined_data, index, sector)
            
            return DataFetchResult(
                success=True,
                data=cleaned_data,
                source=DataSource.FINVIZ
            )
            
        except Exception as e:
            logger.error(f"Finviz fetch error: {e}")
            return DataFetchResult(
                success=False,
                data=pd.DataFrame(),
                source=DataSource.FINVIZ,
                error=str(e)
            )
    
    async def _fetch_from_yahoo(self, index: str, sector: str) -> DataFetchResult:
        """Fetch data from Yahoo Finance as fallback"""
        try:
            # Get tickers for the index/sector combination
            tickers = await self._get_tickers_for_index_sector(index, sector)
            if not tickers:
                return DataFetchResult(
                    success=False,
                    data=pd.DataFrame(),
                    source=DataSource.YAHOO_FINANCE,
                    error="No tickers found"
                )
            
            # Fetch data in chunks
            chunk_size = 50  # Yahoo Finance limit
            all_data = []
            
            for i in range(0, len(tickers), chunk_size):
                chunk = tickers[i:i + chunk_size]
                await self.rate_limiter.wait()
                
                try:
                    # Get basic info
                    ticker_data = yf.Tickers(' '.join(chunk))
                    info = ticker_data.info
                    
                    # Convert to DataFrame
                    df = pd.DataFrame.from_dict(info, orient='index')
                    df['Ticker'] = df.index
                    all_data.append(df)
                    
                except Exception as e:
                    logger.warning(f"Error fetching chunk {i//chunk_size}: {e}")
                    continue
            
            if not all_data:
                return DataFetchResult(
                    success=False,
                    data=pd.DataFrame(),
                    source=DataSource.YAHOO_FINANCE,
                    error="No data returned from Yahoo Finance"
                )
            
            combined_data = pd.concat(all_data, ignore_index=True)
            cleaned_data = self._clean_and_validate_data(combined_data, index, sector)
            
            return DataFetchResult(
                success=True,
                data=cleaned_data,
                source=DataSource.YAHOO_FINANCE
            )
            
        except Exception as e:
            logger.error(f"Yahoo Finance fetch error: {e}")
            return DataFetchResult(
                success=False,
                data=pd.DataFrame(),
                source=DataSource.YAHOO_FINANCE,
                error=str(e)
            )
    
    async def _get_tickers_for_index_sector(self, index: str, sector: str) -> List[str]:
        """Get ticker list for index/sector combination"""
        # This would typically come from a ticker database
        # For now, return common S&P 500 tickers
        sp500_tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'BRK-B',
            'JNJ', 'JPM', 'V', 'PG', 'UNH', 'HD', 'MA', 'DIS', 'PYPL', 'BAC',
            'ADBE', 'CRM', 'NFLX', 'KO', 'PEP', 'TMO', 'ABT', 'AVGO', 'WMT',
            'MRK', 'ACN', 'LLY', 'DHR', 'VZ', 'TXN', 'NEE', 'CMCSA', 'COST',
            'ABBV', 'PFE', 'T', 'CVX', 'HON', 'BMY', 'AMGN', 'QCOM', 'ORCL'
        ]
        return sp500_tickers[:20]  # Limit for testing
    
    def _clean_and_validate_data(self, df: pd.DataFrame, index: str, sector: str) -> pd.DataFrame:
        """Clean and validate the fetched data"""
        try:
            # Remove duplicates
            df = df.loc[:, ~df.columns.duplicated()]
            
            # Ensure we have a Ticker column
            if 'Ticker' not in df.columns:
                logger.warning("No Ticker column found in data")
                return pd.DataFrame()
            
            # Clean numeric columns
            numeric_columns = ['P/E', 'Fwd P/E', 'PEG', 'P/B', 'P/C', 'Price', 'Dividend', 'ROE', 'ROI', 'Insider Own', 'Beta']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    df[col] = df[col].fillna(0)
                    df[col] = df[col].round(3)
            
            # Add metadata
            df['Sector'] = sector
            df['Index'] = index
            df['Last_Updated'] = datetime.now().isoformat()
            
            # Map to schema first
            df = self._map_to_schema(df)
            
            # Convert only string columns to strings, keep numeric columns as numbers
            string_columns = ['Ticker', 'Sector', 'Index', 'Last_Updated', 'Earnings']
            for col in df.columns:
                if col in string_columns:
                    df[col] = df[col].astype(str)
                else:
                    # Keep numeric columns as numbers
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            return df
            
        except Exception as e:
            logger.error(f"Error cleaning data: {e}")
            return pd.DataFrame()
    
    def _map_to_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map columns to our schema"""
        try:
            # Create a mapping for columns that exist
            mapping = {}
            for old_col, new_col in METRIC_SCHEMA.items():
                if old_col in df.columns:
                    mapping[old_col] = new_col
            
            df = df.rename(columns=mapping)
            return df
            
        except Exception as e:
            logger.error(f"Error mapping schema: {e}")
            return df
    
    def _cache_data(self, df: pd.DataFrame, index: str, sector: str):
        """Cache data in Redis with TTL"""
        try:
            redis_manager.save_stock_data(df, index, sector)
            logger.info(f"Cached data for {index}:{sector}")
        except Exception as e:
            logger.error(f"Error caching data: {e}")

class AsyncDataProcessor:
    """Asynchronous data processor for background tasks"""
    
    def __init__(self):
        self.fetcher = DataFetcher()
        self.processing_queue = asyncio.Queue()
        self.results = {}
    
    async def start_processing(self):
        """Start the background processing loop"""
        logger.info("Starting async data processor")
        
        # Start worker tasks
        workers = [
            asyncio.create_task(self._worker(f"worker-{i}"))
            for i in range(3)  # 3 concurrent workers
        ]
        
        try:
            await asyncio.gather(*workers)
        except Exception as e:
            logger.error(f"Processing error: {e}")
        finally:
            logger.info("Async data processor stopped")
    
    async def _worker(self, worker_name: str):
        """Worker task for processing data fetch requests"""
        logger.info(f"Started worker: {worker_name}")
        
        while True:
            try:
                # Get task from queue
                task = await self.processing_queue.get()
                
                if task is None:  # Shutdown signal
                    break
                
                index, sector = task
                logger.info(f"{worker_name} processing {index}:{sector}")
                
                # Fetch data
                async with self.fetcher:
                    result = await self.fetcher.fetch_stock_data(index, sector)
                
                # Store result
                self.results[f"{index}:{sector}"] = result
                
                # Mark task as done
                self.processing_queue.task_done()
                
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                self.processing_queue.task_done()
    
    async def queue_fetch_task(self, index: str, sector: str):
        """Queue a data fetch task"""
        await self.processing_queue.put((index, sector))
    
    async def get_result(self, index: str, sector: str) -> Optional[DataFetchResult]:
        """Get result for a specific index:sector combination"""
        return self.results.get(f"{index}:{sector}")
    
    def _get_stock_list(self, index: str, sector: str) -> List[str]:
        """Get list of stock tickers for the given index and sector"""
        try:
            # For now, return a subset of S&P 500 tickers
            # In a real implementation, this would query a database or API
            sp500_tickers = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'BRK-B',
                'JNJ', 'JPM', 'V', 'PG', 'UNH', 'HD', 'MA', 'DIS', 'PYPL', 'BAC',
                'ADBE', 'CRM', 'NFLX', 'KO', 'PEP', 'TMO', 'ABT', 'AVGO', 'WMT',
                'MRK', 'ACN', 'LLY', 'DHR', 'VZ', 'TXN', 'NEE', 'CMCSA', 'COST',
                'ABBV', 'PFE', 'T', 'CVX', 'HON', 'BMY', 'AMGN', 'QCOM', 'ORCL',
                'INTC', 'AMD', 'CSCO', 'IBM', 'GE', 'F', 'GM', 'XOM', 'SLB', 'EOG'
            ]
            
            # Filter by sector if specified
            if sector != 'Any':
                # This is a simplified sector mapping
                # In a real implementation, you'd have a proper sector database
                sector_tickers = {
                    'Technology': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'ADBE', 'CRM', 'NFLX', 'INTC', 'AMD', 'CSCO', 'IBM', 'ORCL'],
                    'Healthcare': ['JNJ', 'UNH', 'PFE', 'ABT', 'TMO', 'LLY', 'BMY', 'AMGN'],
                    'Financial': ['JPM', 'BAC', 'V', 'MA', 'WFC', 'GS', 'MS', 'BLK'],
                    'Consumer Cyclical': ['AMZN', 'TSLA', 'HD', 'DIS', 'NFLX', 'F', 'GM'],
                    'Industrials': ['GE', 'HON', 'CAT', 'BA', 'MMM', 'UPS', 'FDX'],
                    'Energy': ['XOM', 'CVX', 'SLB', 'EOG', 'COP', 'EOG'],
                    'Basic Materials': ['LIN', 'APD', 'FCX', 'NEM', 'AA'],
                    'Real Estate': ['PLD', 'AMT', 'CCI', 'EQIX', 'DLR'],
                    'Communication Services': ['GOOGL', 'META', 'NFLX', 'DIS', 'CMCSA'],
                    'Utilities': ['NEE', 'DUK', 'SO', 'D', 'AEP'],
                    'Consumer Defensive': ['PG', 'KO', 'PEP', 'WMT', 'COST', 'TGT']
                }
                return sector_tickers.get(sector, sp500_tickers[:20])
            
            return sp500_tickers[:30]  # Limit for performance
            
        except Exception as e:
            logger.error(f"Error getting stock list: {e}")
            return []

    def _fetch_single_stock_data(self, ticker: str) -> pd.DataFrame:
        """Fetch data for a single stock ticker with rate limiting"""
        try:
            # Apply rate limiting
            import asyncio
            try:
                # Try to run rate limiter (non-blocking if possible)
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're in an async context, use the rate limiter
                    loop.create_task(self.rate_limiter.wait())
                else:
                    # If not in async context, just sleep
                    import time
                    time.sleep(1)  # Conservative 1-second delay
            except:
                # Fallback to simple delay
                import time
                time.sleep(1)
            
            # Try Finviz first
            try:
                # Use valuation screener for basic data
                valuation = self.finviz_services['valuation']
                valuation.set_filter(ticker=ticker)
                df = valuation.screener_view()
                
                if not df.empty:
                    # Clean and format the data
                    df = self._clean_single_stock_data(df, ticker)
                    self.rate_limiter.on_error()  # Success, reset backoff
                    return df
                    
            except Exception as e:
                error_msg = str(e).lower()
                if '429' in error_msg or 'rate limit' in error_msg:
                    self.rate_limiter.on_error(429)
                    logger.warning(f"Rate limit hit for {ticker}, backing off")
                else:
                    logger.warning(f"Finviz failed for {ticker}: {e}")
            
            # Fallback to Yahoo Finance (no rate limiting issues)
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                # Create DataFrame from Yahoo data
                data = {
                    'Ticker': [ticker],
                    'Price': [info.get('currentPrice', 0)],
                    'Market Cap': [info.get('marketCap', 0)],
                    'P/E': [info.get('trailingPE', 0)],
                    'Fwd P/E': [info.get('forwardPE', 0)],
                    'PEG': [info.get('pegRatio', 0)],
                    'P/B': [info.get('priceToBook', 0)],
                    'Dividend': [info.get('dividendYield', 0)],
                    'ROE': [info.get('returnOnEquity', 0)],
                    'Beta': [info.get('beta', 0)],
                    'Volume': [info.get('volume', 0)],
                    'Avg Volume': [info.get('averageVolume', 0)],
                    '52W High': [info.get('fiftyTwoWeekHigh', 0)],
                    '52W Low': [info.get('fiftyTwoWeekLow', 0)],
                    'Change': [0],  # Would need to calculate
                    'Sector': [info.get('sector', 'Unknown')],
                    'Index': ['S&P 500']
                }
                
                df = pd.DataFrame(data)
                df = self._clean_single_stock_data(df, ticker)
                return df
                
            except Exception as e:
                logger.warning(f"Yahoo Finance failed for {ticker}: {e}")
            
            # Return empty DataFrame if both sources fail
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error fetching single stock data for {ticker}: {e}")
            return pd.DataFrame()

    def _clean_single_stock_data(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Clean and format single stock data"""
        try:
            # Ensure Ticker column exists
            if 'Ticker' not in df.columns:
                df['Ticker'] = ticker
            
            # Add metadata
            df['Last_Updated'] = datetime.now().isoformat()
            
            # Clean numeric columns
            numeric_columns = ['P/E', 'Fwd P/E', 'PEG', 'P/B', 'P/C', 'Price', 'Dividend', 'ROE', 'ROI', 'Insider Own', 'Beta', 'Volume', 'Market Cap']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    df[col] = df[col].fillna(0)
            
            return df
            
        except Exception as e:
            logger.error(f"Error cleaning single stock data: {e}")
            return pd.DataFrame()
    
    async def shutdown(self):
        """Shutdown the processor"""
        # Send shutdown signals to workers
        for _ in range(3):
            await self.processing_queue.put(None)
        
        # Wait for queue to be processed
        await self.processing_queue.join()

# Global processor instance
data_processor = AsyncDataProcessor()

async def fetch_stock_data_async(index: str, sector: str = 'Any') -> DataFetchResult:
    """Async function to fetch stock data"""
    async with DataFetcher() as fetcher:
        return await fetcher.fetch_stock_data(index, sector)

def fetch_stock_data_sync(index: str, sector: str = 'Any') -> DataFetchResult:
    """Read stock data from Redis only. stocknity-market-data populates stock_data:* keys."""
    try:
        cached_data = redis_manager.get_stock_data(index, sector)
        if not cached_data.empty:
            logger.info(f"Cache hit for {index}:{sector} ({len(cached_data)} records)")
            return DataFetchResult(success=True, data=cached_data, source=DataSource.FINVIZ)

        logger.info(f"No cached stock_data for {index}:{sector} — awaiting market-data service")
        return DataFetchResult(
            success=False,
            data=pd.DataFrame(),
            source=DataSource.FINVIZ,
            error="Awaiting market-data population"
        )
    except Exception as e:
        logger.error(f"Error reading stock_data from Redis: {e}")
        return DataFetchResult(success=False, data=pd.DataFrame(), source=DataSource.FINVIZ, error=str(e))

def _fetch_from_finviz_sync(index: str, sector: str) -> DataFetchResult:
    """Synchronous Finviz fetch"""
    try:
        from finvizfinance.screener.financial import Financial
        from finvizfinance.screener.valuation import Valuation
        from finvizfinance.screener.technical import Technical
        from finvizfinance.screener.ownership import Ownership
        from finvizfinance.screener.performance import Performance
        
        services = {
            'valuation': Valuation(),
            'financial': Financial(),
            'technical': Technical(),
            'ownership': Ownership(),
            'performance': Performance()
        }
        
        all_data = []
        
        for service_name, service in services.items():
            try:
                # Set filters
                filters = {}
                if sector != 'Any':
                    filters["Sector"] = sector
                if index != 'Any':
                    filters["Index"] = index
                
                if filters:
                    service.set_filter(filters_dict=filters)
                
                data = service.screener_view()
                if data is not None and not data.empty:
                    all_data.append(data)
                    logger.debug(f"Successfully fetched {service_name} data")
                
                # Add small delay to respect rate limits
                time.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Error fetching {service_name} data: {e}")
                continue
        
        if not all_data:
            return DataFetchResult(
                success=False,
                data=pd.DataFrame(),
                source=DataSource.FINVIZ,
                error="No data returned from Finviz"
            )
        
        # Combine and clean data
        combined_data = pd.concat(all_data, axis=1)
        cleaned_data = _clean_and_validate_data_sync(combined_data, index, sector)
        
        return DataFetchResult(
            success=True,
            data=cleaned_data,
            source=DataSource.FINVIZ
        )
        
    except Exception as e:
        logger.error(f"Finviz sync fetch error: {e}")
        return DataFetchResult(
            success=False,
            data=pd.DataFrame(),
            source=DataSource.FINVIZ,
            error=str(e)
        )

def _fetch_from_yahoo_sync(index: str, sector: str) -> DataFetchResult:
    """Synchronous Yahoo Finance fetch"""
    try:
        # Get tickers for the index/sector combination
        tickers = _get_tickers_for_index_sector_sync(index, sector)
        if not tickers:
            return DataFetchResult(
                success=False,
                data=pd.DataFrame(),
                source=DataSource.YAHOO_FINANCE,
                error="No tickers found"
            )
        
        # Fetch data in chunks
        chunk_size = 50  # Yahoo Finance limit
        all_data = []
        
        for i in range(0, len(tickers), chunk_size):
            chunk = tickers[i:i + chunk_size]
            
            try:
                # Get basic info
                ticker_data = yf.Tickers(' '.join(chunk))
                info = ticker_data.info
                
                # Convert to DataFrame
                df = pd.DataFrame.from_dict(info, orient='index')
                df['Ticker'] = df.index
                all_data.append(df)
                
                # Add small delay
                import time
                time.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Error fetching chunk {i//chunk_size}: {e}")
                continue
        
        if not all_data:
            return DataFetchResult(
                success=False,
                data=pd.DataFrame(),
                source=DataSource.YAHOO_FINANCE,
                error="No data returned from Yahoo Finance"
            )
        
        combined_data = pd.concat(all_data, ignore_index=True)
        cleaned_data = _clean_and_validate_data_sync(combined_data, index, sector)
        
        return DataFetchResult(
            success=True,
            data=cleaned_data,
            source=DataSource.YAHOO_FINANCE
        )
        
    except Exception as e:
        logger.error(f"Yahoo Finance sync fetch error: {e}")
        return DataFetchResult(
            success=False,
            data=pd.DataFrame(),
            source=DataSource.YAHOO_FINANCE,
            error=str(e)
        )

def _get_tickers_for_index_sector_sync(index: str, sector: str) -> List[str]:
    """Get ticker list for index/sector combination (sync version)"""
    # This would typically come from a ticker database
    # For now, return common S&P 500 tickers
    sp500_tickers = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'BRK-B',
        'JNJ', 'JPM', 'V', 'PG', 'UNH', 'HD', 'MA', 'DIS', 'PYPL', 'BAC',
        'ADBE', 'CRM', 'NFLX', 'KO', 'PEP', 'TMO', 'ABT', 'AVGO', 'WMT',
        'MRK', 'ACN', 'LLY', 'DHR', 'VZ', 'TXN', 'NEE', 'CMCSA', 'COST',
        'ABBV', 'PFE', 'T', 'CVX', 'HON', 'BMY', 'AMGN', 'QCOM', 'ORCL'
    ]
    return sp500_tickers[:20]  # Limit for testing

def _clean_and_validate_data_sync(df: pd.DataFrame, index: str, sector: str) -> pd.DataFrame:
    """Clean and validate the fetched data (sync version)"""
    try:
        # Remove duplicates
        df = df.loc[:, ~df.columns.duplicated()]
        
        # Ensure we have a Ticker column
        if 'Ticker' not in df.columns:
            logger.warning("No Ticker column found in data")
            return pd.DataFrame()
        
        # Clean numeric columns
        numeric_columns = ['P/E', 'Fwd P/E', 'PEG', 'P/B', 'P/C', 'Price', 'Dividend', 'ROE', 'ROI', 'Insider Own', 'Beta']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(0)
                df[col] = df[col].round(3)
        
        # Add metadata
        df['Sector'] = sector
        df['Index'] = index
        df['Last_Updated'] = datetime.now().isoformat()
        
        # Map to schema first
        df = _map_to_schema_sync(df)
        
        # Convert only string columns to strings, keep numeric columns as numbers
        string_columns = ['Ticker', 'Sector', 'Index', 'Last_Updated', 'Earnings']
        for col in df.columns:
            if col in string_columns:
                df[col] = df[col].astype(str)
            else:
                # Keep numeric columns as numbers
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
        
    except Exception as e:
        logger.error(f"Error cleaning data: {e}")
        return pd.DataFrame()

def _map_to_schema_sync(df: pd.DataFrame) -> pd.DataFrame:
    """Map columns to our schema (sync version)"""
    try:
        # Create a mapping for columns that exist
        mapping = {}
        for old_col, new_col in METRIC_SCHEMA.items():
            if old_col in df.columns:
                mapping[old_col] = new_col
        
        df = df.rename(columns=mapping)
        return df
        
    except Exception as e:
        logger.error(f"Error mapping schema: {e}")
        return df

def _cache_data_sync(df: pd.DataFrame, index: str, sector: str):
    """Cache data in Redis with TTL (sync version)"""
    try:
        redis_manager.save_stock_data(df, index, sector)
        logger.info(f"Cached data for {index}:{sector}")
    except Exception as e:
        logger.error(f"Error caching data: {e}")


