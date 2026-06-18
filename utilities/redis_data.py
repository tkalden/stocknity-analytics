import json
import logging
import pandas as pd
import redis
import uuid
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Redis connection configuration from environment variables
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_USERNAME = os.getenv('REDIS_USERNAME', None)  # Optional username
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)  # Required password for production

# Initialize Redis connection
try:
    # Log connection parameters (without sensitive data)
    logging.info(f"Attempting Redis connection to {REDIS_HOST}:{REDIS_PORT}, DB: {REDIS_DB}")
    logging.info(f"Redis username provided: {REDIS_USERNAME is not None}")
    logging.info(f"Redis password provided: {REDIS_PASSWORD is not None}")
    
    # Build connection parameters
    redis_params = {
        'host': REDIS_HOST,
        'port': REDIS_PORT,
        'db': REDIS_DB,
        'decode_responses': True,
        'socket_connect_timeout': 5,  # 5 second timeout
        'socket_timeout': 5
    }
    
    # Add authentication if provided
    if REDIS_USERNAME:
        redis_params['username'] = REDIS_USERNAME
        logging.info(f"Using Redis username: {REDIS_USERNAME}")
    if REDIS_PASSWORD:
        redis_params['password'] = REDIS_PASSWORD
        logging.info("Using Redis password: [HIDDEN]")
    
    logging.info(f"Redis connection parameters: {list(redis_params.keys())}")
    
    r = redis.Redis(**redis_params)
    r.ping()  # Test connection
    REDIS_AVAILABLE = True
    logging.info(f"Redis connection established successfully to {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logging.error(f"Redis connection failed: {e}")
    logging.error(f"Redis connection details - Host: {REDIS_HOST}, Port: {REDIS_PORT}, DB: {REDIS_DB}")
    logging.error(f"Redis auth - Username: {REDIS_USERNAME is not None}, Password: {REDIS_PASSWORD is not None}")
    
    # Try without authentication as fallback
    try:
        logging.info("Attempting Redis connection without authentication as fallback")
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        r.ping()
        REDIS_AVAILABLE = True
        logging.info(f"Redis connection established without authentication to {REDIS_HOST}:{REDIS_PORT}")
    except Exception as fallback_e:
        logging.error(f"Redis fallback connection also failed: {fallback_e}")
        REDIS_AVAILABLE = False
        r = None

class RedisDataManager:
    """Redis-based data manager for stock portfolio application"""
    
    def __init__(self):
        self.r = r
        self.available = REDIS_AVAILABLE
    
    def _generate_id(self) -> str:
        """Generate a unique ID"""
        return str(uuid.uuid4())
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.now().isoformat()
    
    def save_stock_data(self, df: pd.DataFrame, index: str, sector: str) -> bool:
        """Save stock data to Redis"""
        if not self.available:
            logging.warning("Redis not available - skipping save operation")
            return False
        
        try:
            key = f"stock_data:{index}:{sector}"
            data = {
                'data': df.to_dict(orient='records'),
                'index': index,
                'sector': sector,
                'timestamp': self._get_timestamp(),
                'count': len(df)
            }
            self.r.setex(key, 24 * 60 * 60, json.dumps(data))
            
            # Track the data save
            try:
                from utilities.redis_tracker import redis_tracker, DataType, APISource
                redis_tracker.track_data_save(
                    key=key,
                    data_type=DataType.STOCK_DATA,
                    source=APISource.FINVIZ,  # This will be overridden by the caller
                    index=index,
                    sector=sector,
                    record_count=len(df),
                    size_bytes=len(json.dumps(data)),
                    ttl_seconds=24 * 60 * 60
                )
            except Exception as e:
                logging.warning(f"Failed to track stock data save: {e}")
                # Continue without tracking - don't fail the save operation
            
            logging.info(f"Saved stock data for {index}:{sector} with {len(df)} records")
            return True
        except Exception as e:
            logging.error(f"Error saving stock data: {e}")
            return False
    
    def get_stock_data(self, index: str, sector: str) -> pd.DataFrame:
        """Get stock data from Redis"""
        if not self.available:
            logging.warning("Redis not available - returning empty DataFrame")
            return pd.DataFrame()
        
        try:
            key = f"stock_data:{index}:{sector}"
            data = self.r.get(key)
            if data:
                data_dict = json.loads(data)
                
                # Check data freshness (7 days TTL for screener data)
                timestamp = datetime.fromisoformat(data_dict['timestamp'])
                age_hours = (datetime.now() - timestamp).total_seconds() / 3600
                
                if age_hours > 168:  # Data is stale (older than 7 days)
                    logging.info(f"Stock data for {index}:{sector} is stale ({age_hours:.1f} hours old)")
                    return pd.DataFrame()  # Return empty to trigger fresh fetch
                
                df = pd.DataFrame(data_dict['data'])
                
                # Add back the Sector column if it's missing
                if 'Sector' not in df.columns and sector != 'Any':
                    logging.info(f"Adding Sector column for {index}:{sector}")
                    df['Sector'] = sector
                
                # Add back the Index column if it's missing
                if 'Index' not in df.columns:
                    df['Index'] = index
                
                # Track cache hit
                try:
                    from utilities.redis_tracker import redis_tracker
                    redis_tracker.track_data_access(key)
                except Exception as e:
                    logging.warning(f"Failed to track stock data access: {e}")
                
                logging.info(f"Retrieved fresh stock data for {index}:{sector} with {len(df)} records (age: {age_hours:.1f} hours)")
                return df
            else:
                logging.info(f"No stock data found for {index}:{sector}")
                return pd.DataFrame()
        except Exception as e:
            logging.error(f"Error retrieving stock data: {e}")
            return pd.DataFrame()
    
    def get_stock_data_any_age(self, index: str, sector: str) -> pd.DataFrame:
        """Get stock data from Redis regardless of age (for immediate display)"""
        if not self.available:
            logging.warning("Redis not available - returning empty DataFrame")
            return pd.DataFrame()
        
        try:
            key = f"stock_data:{index}:{sector}"
            data = self.r.get(key)
            if data:
                data_dict = json.loads(data)
                df = pd.DataFrame(data_dict['data'])
                
                # Add back the Sector column if it's missing
                if 'Sector' not in df.columns and sector != 'Any':
                    logging.info(f"Adding Sector column for {index}:{sector}")
                    df['Sector'] = sector
                
                # Add back the Index column if it's missing
                if 'Index' not in df.columns:
                    df['Index'] = index
                
                # Calculate age for logging
                timestamp = datetime.fromisoformat(data_dict['timestamp'])
                age_minutes = (datetime.now() - timestamp).total_seconds() / 60
                
                logging.info(f"Retrieved cached stock data for {index}:{sector} with {len(df)} records (age: {age_minutes:.1f} minutes)")
                return df
            else:
                logging.info(f"No cached stock data found for {index}:{sector}")
                return pd.DataFrame()
        except Exception as e:
            logging.error(f"Error retrieving cached stock data: {e}")
            return pd.DataFrame()
    
    def save_average_metrics(self, df: pd.DataFrame) -> bool:
        """Save average metrics data"""
        if not self.available:
            logging.warning("Redis not available - skipping save operation")
            return False
        
        try:
            key = "average_metrics"
            data = {
                'data': df.to_dict(orient='records'),
                'timestamp': self._get_timestamp(),
                'count': len(df)
            }
            # Save with 24-hour TTL
            self.r.setex(key, 24 * 60 * 60, json.dumps(data))
            logging.info(f"Saved average metrics with {len(df)} records")
            return True
        except Exception as e:
            logging.error(f"Error saving average metrics: {e}")
            return False
    
    def get_average_metrics(self) -> pd.DataFrame:
        """Get average metrics data"""
        if not self.available:
            logging.warning("Redis not available - returning empty DataFrame")
            return pd.DataFrame()
        
        try:
            key = "average_metrics"
            data = self.r.get(key)
            if data:
                data_dict = json.loads(data)
                df = pd.DataFrame(data_dict['data'])
                logging.info(f"Retrieved average metrics with {len(df)} records")
                return df
            else:
                logging.info("No average metrics found")
                return pd.DataFrame()
        except Exception as e:
            logging.error(f"Error retrieving average metrics: {e}")
            return pd.DataFrame()
    
    def save_user(self, email: str, name: str, password: str) -> bool:
        """Save user data"""
        if not self.available:
            logging.warning("Redis not available - skipping save operation")
            return False
        
        try:
            user_data = {
                'email': email,
                'name': name,
                'password': password,
                'created_at': self._get_timestamp(),
                'id': self._generate_id()
            }
            self.r.hset('users', email, json.dumps(user_data))
            logging.info(f"Saved user data for {email}")
            return True
        except Exception as e:
            logging.error(f"Error saving user data: {e}")
            return False
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        if not self.available:
            logging.warning("Redis not available - returning None")
            return None
        
        try:
            user_data = self.r.hget('users', email)
            if user_data:
                return json.loads(user_data)
            else:
                logging.info(f"No user found for email: {email}")
                return None
        except Exception as e:
            logging.error(f"Error retrieving user data: {e}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by user_id"""
        if not self.available:
            logging.warning("Redis not available - returning None")
            return None

        try:
            # Get all users and find the one with matching user_id
            all_users = self.r.hgetall('users')
            for email, user_data_str in all_users.items():
                user_data = json.loads(user_data_str)
                if user_data.get('id') == user_id:
                    logging.info(f"Found user with ID: {user_id}")
                    return user_data
            
            logging.info(f"No user found for user_id: {user_id}")
            return None
        except Exception as e:
            logging.error(f"Error retrieving user data by ID: {e}")
            return None
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user"""
        user = self.get_user_by_email(email)
        if user and user.get('password') == password:
            return user
        return None
    
    def save_portfolio(self, user_id: str, portfolio_data: pd.DataFrame) -> str:
        """Save portfolio data"""
        if not self.available:
            logging.warning("Redis not available - skipping save operation")
            return ""
        
        try:
            portfolio_id = self._generate_id()
            portfolio_key = f"portfolio:{portfolio_id}"
            
            data = {
                'portfolio_id': portfolio_id,
                'user_id': user_id,
                'data': portfolio_data.to_dict(orient='records'),
                'created_at': self._get_timestamp(),
                'count': len(portfolio_data)
            }
            
            # Save portfolio data (no TTL - persistent user data)
            self.r.set(portfolio_key, json.dumps(data))
            
            # Add to user's portfolio list (no TTL - persistent user data)
            user_portfolios_key = f"user_portfolios:{user_id}"
            self.r.sadd(user_portfolios_key, portfolio_id)
            
            logging.info(f"Saved portfolio {portfolio_id} for user {user_id}")
            return portfolio_id
        except Exception as e:
            logging.error(f"Error saving portfolio: {e}")
            return ""
    
    def get_portfolio_by_id(self, portfolio_id: str) -> Optional[Dict]:
        """Get a specific portfolio by ID"""
        if not self.available:
            logging.warning("Redis not available - returning None")
            return None
        
        try:
            portfolio_key = f"portfolio:{portfolio_id}"
            portfolio_data = self.r.get(portfolio_key)
            if portfolio_data:
                return json.loads(portfolio_data)
            else:
                logging.info(f"No portfolio found for ID: {portfolio_id}")
                return None
        except Exception as e:
            logging.error(f"Error retrieving portfolio: {e}")
            return None

    def delete_portfolio(self, portfolio_id: str, user_id: str) -> bool:
        """Delete a specific portfolio"""
        if not self.available:
            logging.warning("Redis not available - skipping delete operation")
            return False
        
        try:
            portfolio_key = f"portfolio:{portfolio_id}"
            
            # Check if portfolio exists and belongs to user
            portfolio_data = self.r.get(portfolio_key)
            if not portfolio_data:
                logging.warning(f"Portfolio {portfolio_id} not found")
                return False
            
            portfolio_dict = json.loads(portfolio_data)
            if portfolio_dict.get('user_id') != user_id:
                logging.warning(f"Portfolio {portfolio_id} does not belong to user {user_id}")
                return False
            
            # Delete portfolio data
            self.r.delete(portfolio_key)
            
            # Remove from user's portfolio list
            user_portfolios_key = f"user_portfolios:{user_id}"
            self.r.srem(user_portfolios_key, portfolio_id)
            
            logging.info(f"Deleted portfolio {portfolio_id} for user {user_id}")
            return True
        except Exception as e:
            logging.error(f"Error deleting portfolio: {e}")
            return False

    def get_portfolios_by_user_id(self, user_id: str) -> List[Dict]:
        """Get all portfolios for a user"""
        if not self.available:
            logging.warning("Redis not available - returning empty list")
            return []
        
        try:
            user_portfolios_key = f"user_portfolios:{user_id}"
            portfolio_ids = self.r.smembers(user_portfolios_key)
            
            portfolios = []
            for portfolio_id in portfolio_ids:
                portfolio_key = f"portfolio:{portfolio_id}"
                portfolio_data = self.r.get(portfolio_key)
                if portfolio_data:
                    portfolios.append(json.loads(portfolio_data))
            
            logging.info(f"Retrieved {len(portfolios)} portfolios for user {user_id}")
            return portfolios
        except Exception as e:
            logging.error(f"Error retrieving portfolios: {e}")
            return []
    
    def save_subscription(self, email: str) -> bool:
        """Save subscription data"""
        if not self.available:
            logging.warning("Redis not available - skipping save operation")
            return False
        
        try:
            subscription_data = {
                'email': email,
                'subscribed_at': self._get_timestamp()
            }
            self.r.hset('subscriptions', email, json.dumps(subscription_data))
            logging.info(f"Saved subscription for {email}")
            return True
        except Exception as e:
            logging.error(f"Error saving subscription: {e}")
            return False
    
    def get_subscription_by_email(self, email: str) -> Optional[Dict]:
        """Get subscription by email"""
        if not self.available:
            logging.warning("Redis not available - returning None")
            return None
        
        try:
            subscription_data = self.r.hget('subscriptions', email)
            if subscription_data:
                return json.loads(subscription_data)
            else:
                logging.info(f"No subscription found for email: {email}")
                return None
        except Exception as e:
            logging.error(f"Error retrieving subscription: {e}")
            return None
    
    def save_annual_returns(self, df: pd.DataFrame) -> bool:
        """Save annual returns data"""
        if not self.available:
            logging.warning("Redis not available - skipping save operation")
            return False
        
        try:
            key = "annual_returns"
            data = {
                'data': df.to_dict(orient='records'),
                'timestamp': self._get_timestamp(),
                'count': len(df),
                'source': 'yahoo_finance',
                'version': '1.0'
            }
            # Save with 48-hour TTL (172800 seconds) for longer caching
            self.r.setex(key, 48 * 60 * 60, json.dumps(data))
            logging.info(f"Saved annual returns with {len(df)} records (TTL: 48h)")
            return True
        except Exception as e:
            logging.error(f"Error saving annual returns: {e}")
            return False
    
    def get_annual_returns(self) -> pd.DataFrame:
        """Get annual returns data from Redis"""
        if not self.available:
            logging.warning("Redis not available - returning empty DataFrame")
            return pd.DataFrame()
        
        try:
            key = "annual_returns"
            data = self.r.get(key)
            if data:
                data_dict = json.loads(data)
                df = pd.DataFrame(data_dict['data'])
                
                # Log cache hit with TTL info
                ttl = self.r.ttl(key)
                if ttl > 0:
                    hours_remaining = ttl // 3600
                    minutes_remaining = (ttl % 3600) // 60
                    logging.info(f"Retrieved annual returns with {len(df)} records (Cache expires in {hours_remaining}h {minutes_remaining}m)")
                else:
                    logging.info(f"Retrieved annual returns with {len(df)} records (Cache expired)")
                
                return df
            else:
                logging.info("No annual returns data found in Redis")
                return pd.DataFrame()
        except Exception as e:
            logging.error(f"Error retrieving annual returns: {e}")
            return pd.DataFrame()
    
    def get_annual_returns_cache_status(self) -> Dict[str, Any]:
        """Get detailed cache status for annual returns"""
        if not self.available:
            return {"status": "redis_unavailable"}
        
        try:
            key = "annual_returns"
            data = self.r.get(key)
            ttl = self.r.ttl(key)
            
            if data:
                data_dict = json.loads(data)
                return {
                    "status": "cached",
                    "ttl_seconds": ttl,
                    "ttl_human": f"{ttl//3600}h {(ttl%3600)//60}m" if ttl > 0 else "Expired",
                    "count": data_dict.get('count', 0),
                    "timestamp": data_dict.get('timestamp', ''),
                    "source": data_dict.get('source', 'unknown'),
                    "version": data_dict.get('version', 'unknown')
                }
            else:
                return {"status": "not_cached"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def clear_annual_returns(self) -> bool:
        """Clear annual returns data from Redis"""
        if not self.available:
            logging.warning("Redis not available - skipping clear operation")
            return False
        
        try:
            key = "annual_returns"
            result = self.r.delete(key)
            if result:
                logging.info("Cleared annual returns data from Redis")
            else:
                logging.info("No annual returns data found to clear")
            return True
        except Exception as e:
            logging.error(f"Error clearing annual returns: {e}")
            return False
    
    def extend_annual_returns_cache(self, hours: int = 24) -> bool:
        """Extend the TTL of annual returns cache"""
        if not self.available:
            logging.warning("Redis not available - skipping extend operation")
            return False
        
        try:
            key = "annual_returns"
            if self.r.exists(key):
                self.r.expire(key, hours * 60 * 60)
                logging.info(f"Extended annual returns cache TTL by {hours} hours")
                return True
            else:
                logging.warning("No annual returns cache found to extend")
                return False
        except Exception as e:
            logging.error(f"Error extending annual returns cache: {e}")
            return False
    
    def clear_expired_data(self) -> int:
        """Clear expired data (optional maintenance function)"""
        if not self.available:
            return 0
        
        try:
            # This is a simple implementation - in production you might want more sophisticated cleanup
            keys = self.r.keys("stock_data:*")
            expired_count = 0
            for key in keys:
                if not self.r.exists(key):
                    expired_count += 1
            logging.info(f"Cleared {expired_count} expired keys")
            return expired_count
        except Exception as e:
            logging.error(f"Error clearing expired data: {e}")
            return 0

    def save_strength_data(self, df, cache_key):
        """Save strength data to Redis"""
        try:
            # Convert DataFrame to JSON string
            data_json = df.to_json(orient='records')
            # Save with 24-hour TTL (86400 seconds)
            self.r.setex(cache_key, 86400, data_json)
            logging.debug(f"Saved strength data to Redis: {cache_key}")
            return True
        except Exception as e:
            logging.error(f"Error saving strength data to Redis: {e}")
            return False

    def get_strength_data(self, cache_key):
        """Get strength data from Redis"""
        try:
            data_json = self.r.get(cache_key)
            if data_json:
                df = pd.read_json(data_json, orient='records')
                logging.debug(f"Retrieved strength data from Redis: {cache_key}")
                return df
            return pd.DataFrame()
        except Exception as e:
            logging.error(f"Error retrieving strength data from Redis: {e}")
            return pd.DataFrame()

    def clear_strength_cache(self, prefix):
        """Clear all strength data from cache"""
        try:
            pattern = f"{prefix}:*"
            keys = self.r.keys(pattern)
            if keys:
                self.r.delete(*keys)
                logging.info(f"Cleared {len(keys)} strength data cache entries")
            else:
                logging.info("No strength data cache entries found to clear")
        except Exception as e:
            logging.error(f"Error clearing strength cache: {e}")

    def get_strength_cache_status(self):
        """Get status of strength data cache"""
        try:
            pattern = "strength_data:*"
            keys = self.r.keys(pattern)
            cache_info = {}
            
            for key in keys:
                ttl = self.r.ttl(key)
                cache_info[key] = {
                    'ttl': ttl,
                    'expires_in': f"{ttl//3600}h {(ttl%3600)//60}m" if ttl > 0 else "Expired"
                }
            
            return cache_info
        except Exception as e:
            logging.error(f"Error getting strength cache status: {e}")
            return {}

# Global instance
redis_manager = RedisDataManager() 