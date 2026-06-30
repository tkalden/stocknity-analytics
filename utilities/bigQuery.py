import logging
import pandas as pd
from utilities.redis_data import redis_manager

logging.basicConfig(level=logging.INFO)

def write_to_bigquery(df, table_id):
    """Save data to Redis (replacing BigQuery)"""
    logging.info('Saving data to Redis')
    # For now, we'll save to a generic key based on table_id
    # In a more sophisticated implementation, you might want to parse table_id
    return redis_manager.save_stock_data(df, "default", "default")

def get_stock_data(index, sector):
    """Get stock data from Redis"""
    logging.info(f'Getting Stock data for Sector {sector} and Index {index}')
    return redis_manager.get_stock_data(index, sector)

def run_query(query, query_parameters):
    """Placeholder for query functionality - not needed with Redis"""
    logging.warning("Query functionality not implemented for Redis - returning empty DataFrame")
    return pd.DataFrame()

def get_average_metric_by_sector(sector):
    """Get average metrics by sector from Redis"""
    logging.info(f'Getting Average metric data for Sector {sector}')
    df = redis_manager.get_average_metrics()
    if not df.empty and 'Sector' in df.columns:
        return df[df['Sector'] == sector]
    return pd.DataFrame()

def get_portfolios_by_user_id(user_id):
    """Get portfolios by user ID from Redis"""
    portfolios = redis_manager.get_portfolios_by_user_id(user_id)
    if portfolios:
        # Convert to DataFrame format expected by the application
        all_records = []
        for portfolio in portfolios:
            if 'data' in portfolio:
                for record in portfolio['data']:
                    record['portfolio_id'] = portfolio['portfolio_id']
                    record['user_id'] = portfolio['user_id']
                    all_records.append(record)
        return pd.DataFrame(all_records)
    return pd.DataFrame()

def get_subscription_by_id(email):
    """Get subscription by email from Redis"""
    subscription = redis_manager.get_subscription_by_email(email)
    if subscription:
        return pd.DataFrame([subscription])
    return pd.DataFrame()

def get_portfolio_by_id(portfolio_id):
    """Get portfolio by ID from Redis"""
    # This would need to be implemented in RedisDataManager
    logging.warning("get_portfolio_by_id not implemented for Redis")
    return pd.DataFrame()

def get_average_metric():
    """Get all average metrics from Redis"""
    return redis_manager.get_average_metrics()

def get_annual_return():
    """Get annual returns from Redis"""
    return redis_manager.get_annual_returns()

def get_query(index, sector):
    """Placeholder for query generation - not needed with Redis"""
    return ""

def insert_rows(table_id, rows_to_insert):
    """Insert rows into Redis (replacing BigQuery)"""
    logging.info('Inserting rows into Redis')
    # Convert rows to DataFrame and save
    if rows_to_insert:
        df = pd.DataFrame(rows_to_insert)
        return redis_manager.save_stock_data(df, "default", "default")
    return False