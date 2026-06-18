import logging
import json
import pandas as pd

import enums.enum as enum
from services.data_fetcher import fetch_stock_data_sync
from services.strengthCalculator import StrengthCalculator
from utilities.constant import SECTORS
from utilities.redis_data import redis_manager
from utilities.redis_tracker import redis_tracker

strengthCalculator = StrengthCalculator()
# Using new async data fetcher instead of sourceDataMapperService


class chart():
     # init method or constructor
    def __init__(self):
        self.index = 'S&P 500' #default
        self.sectors = SECTORS
 
    def get_chart_data(self, stock_type):
        """Get chart data with caching to avoid multiple API calls"""
        # Check cache first
        cache_key = f"chart_data:{stock_type}:{self.index}"
        cached_data = self._get_chart_from_cache(cache_key)
        
        if cached_data:
            logging.info(f'Retrieved chart data from cache for {stock_type}')
            redis_tracker.track_data_access(cache_key)
            return cached_data
        
        # If not in cache, calculate and cache
        logging.info(f'Calculating chart data for {stock_type} (not in cache)')
        top_dict = self._calculate_chart_data(stock_type)
        
        # Cache the result
        self._save_chart_to_cache(cache_key, top_dict)
        
        return top_dict

    def _get_chart_from_cache(self, cache_key):
        """Get chart data from Redis cache"""
        try:
            cached_data = redis_manager.r.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logging.error(f"Error getting chart data from cache: {e}")
            return None

    def _save_chart_to_cache(self, cache_key, chart_data):
        """Save chart data to Redis cache"""
        try:
            # Cache for 24 hours (86400 seconds)
            redis_manager.r.setex(cache_key, 86400, json.dumps(chart_data))
            from utilities.redis_tracker import DataType, APISource
            redis_tracker.track_data_save(
                cache_key, 
                DataType.CHART_DATA, 
                APISource.CHART_SERVICE,
                index=self.index,
                record_count=len(chart_data),
                ttl_seconds=86400
            )
            logging.info(f'Cached chart data with key: {cache_key}')
        except Exception as e:
            logging.error(f"Error saving chart data to cache: {e}")

    def _calculate_chart_data(self, stock_type):
        """Calculate chart data for all sectors using individual API calls with caching"""
        top_dict = []
        
        # Process each sector individually (but with caching)
        for sector in self.sectors:
            try:
                values, labels = self._get_sector_data(stock_type, sector)
                top_dict.append({"id": sector, "values": values, "labels": labels, "title": sector})
            except Exception as e:
                logging.error(f"Error processing sector {sector}: {e}")
                top_dict.append({"id": sector, "values": [], "labels": [], "title": sector})
        
        logging.info(f'Calculated chart data for {len(top_dict)} sectors')
        return top_dict



    def _calculate_value_metrics(self, df):
        """Calculate value stock metrics using industry-standard ratios"""
        try:
            if not df.empty and self._has_required_columns(df, ["Ticker", "pe", "pb", "dividend"]):
                # Calculate Value Score using industry-standard metrics
                # Lower P/E and P/B ratios are better for value stocks
                df['pe_numeric'] = pd.to_numeric(df['pe'], errors='coerce').fillna(50)
                df['pb_numeric'] = pd.to_numeric(df['pb'], errors='coerce').fillna(10)
                df['dividend_numeric'] = pd.to_numeric(df['dividend'], errors='coerce').fillna(0)
                
                # Value Score using industry-standard metrics (0-100 scale)
                # Components: P/E ratio (40%), P/B ratio (30%), Dividend Yield (30%)
                # Lower P/E and P/B ratios are better for value stocks
                pe_score = (1 / df['pe_numeric'].clip(lower=1)) * 40
                pb_score = (1 / df['pb_numeric'].clip(lower=0.1)) * 30
                dividend_score = (df['dividend_numeric'] * 100) * 30
                
                df['value_score'] = (pe_score + pb_score + dividend_score).round(1)
                
                # Sort by value score (higher is better)
                value_data = df.nlargest(5, 'value_score')
                return self._extract_lists(value_data["value_score"], value_data["Ticker"])
            else:
                logging.warning(f"Missing required columns for value metrics")
                return [], []
        except Exception as e:
            logging.error(f"Error calculating value metrics: {e}")
            return [], []

    def _calculate_growth_metrics(self, df):
        """Calculate growth stock metrics using industry-standard ratios"""
        try:
            if not df.empty and self._has_required_columns(df, ["Ticker", "pe", "fpe"]):
                # Calculate Growth Score using industry-standard metrics
                df['pe_numeric'] = pd.to_numeric(df['pe'], errors='coerce').fillna(50)
                df['fpe_numeric'] = pd.to_numeric(df['fpe'], errors='coerce').fillna(50)
                
                # Handle PEG ratio if available
                if 'peg' in df.columns:
                    df['peg_numeric'] = pd.to_numeric(df['peg'], errors='coerce').fillna(5)
                    peg_component = (1 / df['peg_numeric'].clip(lower=0.1)) * 30
                else:
                    peg_component = 0
                
                # Handle Sales Growth if available
                if 'Sales Past 5Y' in df.columns:
                    df['sales_growth'] = df['Sales Past 5Y'].astype(str).str.replace('%', '').str.replace('-', '0')
                    df['sales_growth_numeric'] = pd.to_numeric(df['sales_growth'], errors='coerce').fillna(0) / 100
                    sales_component = (df['sales_growth_numeric'].clip(upper=1)) * 40
                else:
                    sales_component = 0
                
                # Growth Score using industry-standard metrics (0-100 scale)
                # Components: Sales Growth (40%), PEG ratio (30%), Forward P/E (30%)
                # Higher sales growth and lower PEG/FPE ratios are better for growth stocks
                fpe_score = (1 / df['fpe_numeric'].clip(lower=1)) * 30
                
                df['growth_score'] = (sales_component + peg_component + fpe_score).round(1)
                
                # Sort by growth score (higher is better)
                growth_data = df.nlargest(5, 'growth_score')
                return self._extract_lists(growth_data["growth_score"], growth_data["Ticker"])
            else:
                logging.warning(f"Missing required columns for growth metrics")
                return [], []
        except Exception as e:
            logging.error(f"Error calculating growth metrics: {e}")
            return [], []

    def _calculate_dividend_data(self, df):
        """Calculate dividend-based chart data"""
        try:
            if not df.empty and self._has_required_columns(df, ["Ticker", "dividend"]):
                dividend_data = df.sort_values(by="dividend", ascending=False).head(5)
                # Convert dividend values to percentages for better display
                dividend_percentages = dividend_data["dividend"].astype(float) * 100
                return self._extract_lists(dividend_percentages, dividend_data["Ticker"])
            else:
                logging.warning(f"Missing required columns in dividend data")
                return [], []
        except Exception as e:
            logging.error(f"Error in dividend calculation: {e}")
            return [], []

    def _get_sector_data(self, stock_type, sector):
        """Get chart data for a specific sector and stock type (legacy method - kept for compatibility)"""
        if stock_type == enum.StockType.VALUE.value:
            return self._get_value_metrics(sector)
        elif stock_type == enum.StockType.GROWTH.value:
            return self._get_growth_metrics(sector)
        elif stock_type == enum.StockType.DIVIDEND.value:
            return self._get_dividend_data(sector)
        else:
            return [], []

    def _get_value_metrics(self, sector):
        """
        Value score: P/E (40%) + dividend yield (40%) + return stability (20%).
        Each term uses fillna(0) — missing columns contribute 0, not errors.
        Works with any source; sources providing more columns rank more accurately.
        """
        try:
            result = fetch_stock_data_sync(index=self.index, sector=sector)
            if result.success and not result.data.empty:
                df = result.data.copy()
                pe  = pd.to_numeric(df.get('pe',  None), errors='coerce').fillna(0)
                div = pd.to_numeric(df.get('dividend', 0), errors='coerce').fillna(0)
                ret = pd.to_numeric(df.get('annual_return', 0), errors='coerce').fillna(0)

                # Lower P/E = better value; 0 when P/E not provided
                pe_score  = (1 / pe.clip(lower=1)).where(pe > 0, 0) * 40
                div_score = (div * 100).clip(upper=40)
                # Stability bonus: low or moderate positive return preferred over high volatility
                stab_score = (50 - ret.clip(-50, 50)) * 0.4

                df['value_score'] = (pe_score + div_score + stab_score).round(1)
                top = df.nlargest(5, 'value_score')
                return self._extract_lists(top['value_score'], top['Ticker'])
            return [], []
        except Exception as e:
            logging.error(f"Value metrics error {sector}: {e}")
            return [], []

    def _get_growth_metrics(self, sector):
        """
        Growth score: annual return (primary) + today's change (secondary).
        Both fillna(0) — source need not provide both.
        """
        try:
            result = fetch_stock_data_sync(index=self.index, sector=sector)
            if result.success and not result.data.empty:
                df = result.data.copy()
                ret   = pd.to_numeric(df.get('annual_return', 0), errors='coerce').fillna(0)
                today = pd.to_numeric(df.get('today_change',  0), errors='coerce').fillna(0)

                df['growth_score'] = (
                    ret.clip(-100, 500) * 0.9 +
                    today.clip(-10, 10) * 0.1
                ).round(1)
                top = df.nlargest(5, 'growth_score')
                return self._extract_lists(top['growth_score'], top['Ticker'])
            return [], []
        except Exception as e:
            logging.error(f"Growth metrics error {sector}: {e}")
            return [], []

    def _get_dividend_data(self, sector):
        """Top 5 by dividend yield, displayed as percentage."""
        try:
            result = fetch_stock_data_sync(index=self.index, sector=sector)
            if result.success and not result.data.empty:
                df = result.data.copy()
                df['div'] = pd.to_numeric(df.get('dividend', 0), errors='coerce').fillna(0)
                top = df.nlargest(5, 'div')
                pct = (top['div'] * 100).round(2)
                return self._extract_lists(pct, top['Ticker'])
            return [], []
        except Exception as e:
            logging.error(f"Dividend data error {sector}: {e}")
            return [], []

    def _has_required_columns(self, df, required_columns):
        """Check if DataFrame has required columns"""
        return not df.empty and all(col in df.columns for col in required_columns)

    def _extract_lists(self, values_series, labels_series):
        """Extract values and labels as lists"""
        values = values_series.tolist() if hasattr(values_series, 'tolist') else []
        labels = labels_series.tolist() if hasattr(labels_series, 'tolist') else []
        return values, labels
    
    

    
