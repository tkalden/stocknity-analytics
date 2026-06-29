import logging

import numpy as np
import pandas as pd

from enums.enum import StockType
from services.annualReturn import AnnualReturn
from utilities.redis_data import redis_manager

# Using new async data fetcher instead of SourceDataMapperService
AnnualReturn = AnnualReturn()

# Documented canonical schema written by the stocknity-market-data service
# (ScreenerDataAggregator) into the stock_data:{index}:{sector} Redis keys.
CANONICAL_COLUMNS = [
    "Ticker", "pe", "pb", "fpe", "peg",
    "dividend", "annual_return", "today_change", "price",
]


class CanonicalDataUnavailable(Exception):
    """Raised when the canonical stock_data:* key is missing, empty, or malformed.

    Flask is read-only: it must NOT refetch from yfinance/FMP when the
    market-data service has not yet populated the canonical key. Endpoints
    catch this and surface HTTP 503.
    """


class StrengthCalculator:

    def __init__(self):
        self.cache_key_prefix = "strength_data"

    def _read_canonical_data(self, index, sector):
        """Read the canonical stock_data:{index}:{sector} key into a DataFrame.

        Raises CanonicalDataUnavailable if the key is missing/empty or does not
        contain the documented columns. Never writes anything back.
        """
        df = redis_manager.get_stock_data(index, sector)
        if df is None or df.empty:
            raise CanonicalDataUnavailable(
                f"Canonical stock_data:{index}:{sector} is missing or empty. "
                "Awaiting population by the stocknity-market-data service."
            )

        missing = [col for col in CANONICAL_COLUMNS if col not in df.columns]
        if missing:
            raise CanonicalDataUnavailable(
                f"Canonical stock_data:{index}:{sector} is missing required "
                f"columns: {missing}. Expected schema: {CANONICAL_COLUMNS}."
            )

        return df

    def calculate_strength_value(self, stock_type, sector, index):
        """Compute strength in-memory from canonical Redis data. READ-ONLY.

        Reads stock_data:{index}:{sector} (written by the market-data service),
        validates the documented schema, merges return data and computes the
        strength score in-memory. Nothing is written back to Redis.

        Raises:
            CanonicalDataUnavailable: if the canonical key is missing/empty or
                does not match the documented schema. Callers surface HTTP 503.
        """
        logging.debug(f"Calculating strength value for {stock_type} Stock")

        df = self._read_canonical_data(index, sector)

        # Enrich with return/risk data (in-memory merge).
        df = AnnualReturn.update_with_return_data(df)

        # Create average metrics from the data
        if not df.empty:
            avg_metric_df = df[["dividend", "pe", "fpe", "pb", "beta", "return_risk_ratio"]].apply(pd.to_numeric, errors='coerce').mean()
        else:
            avg_metric_df = pd.Series({
                "dividend": 0,
                "pe": 0,
                "fpe": 0,
                "pb": 0,
                "beta": 0,
                "return_risk_ratio": 0
            })

        # Calculate strength (in-memory only)
        df = self._calculate_strength(df, avg_metric_df, stock_type)

        return df

    def _calculate_strength(self, df, avg_metric_df, stock_type):
        """Calculate strength values for the dataframe"""
        if df.empty:
            return df

        attributes = ["dividend", "pe", "fpe", "pb", "beta", "return_risk_ratio"]
        df["strength"] = 0

        for col in attributes:
            if col not in df.columns:
                logging.warning(f"Column {col} not found in DataFrame, skipping")
                continue

            df[col].replace('nan', np.nan, inplace=True)
            df[col].replace('None', np.nan, inplace=True)

            if col == 'beta':
                df["strength"] = df["strength"] - np.where(df[col].isnull(), 0, df[col].astype(float))
            elif col == 'return_risk_ratio':
                df["strength"] = df["strength"] + np.where(df[col].isnull(), 0, df[col].astype(float))
            else:
                if col in avg_metric_df and avg_metric_df[col] != 0:
                    new_col = np.where(df[col].isnull(), 0, df[col].astype(float) - avg_metric_df[col])
                    new_col = np.divide(1, avg_metric_df[col]) * new_col  # percentage change
                    if col == 'dividend':
                        df["strength"] = df["strength"] + new_col
                    else:
                        df["strength"] = df["strength"] - new_col

        if stock_type == StockType.VALUE.value:
            df["strength"] = 1 * df["strength"]
        elif stock_type == StockType.GROWTH.value:
            df["strength"] = -1 * df["strength"]
        else:
            raise ValueError("Stock Type must be Value or Growth")

        df = df.replace(np.nan, 0)
        df = np.round(df, decimals=3)
        df = df.sort_values(by=["strength"], ascending=[False])

        return df
