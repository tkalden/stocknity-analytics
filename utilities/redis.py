
import json
import logging

import pandas as pd
import redis

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0)
logging.basicConfig(level = logging.INFO)

def fetch_data_from_redis(key):
    logging.info(f"Data found in Redis for key {key}")
    # Fetch data by key
    data = r.get(key)
    # Convert data from bytes to string
    data_str = data.decode('utf-8')
    # Convert data from string to JSON object
    data_json = json.loads(data_str)
    # Process the data as needed
    df = pd.DataFrame.from_dict(data_json)
    logging.info('Total %s Data fetched from Redis', df.shape[0])
    return df
   

def check_data_from_redis(key):
    return r.exists(key)

def save_data_to_redis(data,key):
    logging.info('Saving data to Redis for Key %s', key)
    # Save the data to Redis with a TTL of 24 hours
    r.setex(key, 24 * 60 * 60, json.dumps(data.to_dict(orient='records')))
    logging.info('Total %s Data Saved To Redis', data.shape[0])

def save_data_to_redis_until_delete(data,key):
    logging.info('Saving data to Redis for Key %s', key)
    # Save the data to Redis with a TTL of 24 hours
    logging.info('Total %s Data Saved To Redis', data.shape[0])
