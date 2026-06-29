import logging
import uuid

import numpy as np
import pandas as pd
from flask import flash

import utilities.helper as helper
from services.annualReturn import AnnualReturn
from services.optimization import optimization
from services.advanced_optimization import AdvancedPortfolioOptimizer
from services.backtesting import PortfolioBacktester
from utilities.pickle import pickle
from utilities.redis_data import redis_manager

optimization = optimization()
annualReturn = AnnualReturn()
advanced_optimizer = AdvancedPortfolioOptimizer()
backtester = PortfolioBacktester()

class portfolio():
     # init method or constructor
    def __init__(self):
        self.optimized_df = pd.DataFrame()
        self.portfolio_redis_key = 'portfolio'
        self.optimal_number_stocks = 0
        self.previous_highest_expected_return = 0
        self.threshold = 0
        self.desired_return = 0
        self.portfolio_list = []

    def build_portfolio_from_user_input_tickers(self, df, selected_ticker_list, desired_return, investing_amount,risk_tolerance):
        df = df[df.Ticker.isin(selected_ticker_list)]
        df = df[(df['strength'] > 0) & (df['expected_annual_return'].astype(float) > 0)]
        df = annualReturn.get_risk_tolerance_data(risk_tolerance,df)
        self.threshold = len(selected_ticker_list)
        self.desired_return = desired_return
        self.optimized_df = df #initialize the df
        self.optimized_df = optimization.optimize_expected_return(self.optimized_df,
            number_of_stocks=len(selected_ticker_list),threshold = len(selected_ticker_list), desired_return = desired_return)
        self.optimized_df  = self.calculate_portfolio_value_and_share(investing_amount)
        return self.optimized_df 

    def calculate_portfolio_value_and_share(self, investing_amount):
        self.calculate_portfolio_value_distribution(investing_amount)
        self.total_share()
        portfolio = np.round(self.optimized_df, decimals=3)
        
        # Get required attributes and filter to only include columns that exist
        required_attributes = helper.portfolio_attributes()
        existing_columns = [col for col in required_attributes if col in portfolio.columns]
        
        # If weighted_expected_return is missing, calculate it
        if 'weighted_expected_return' not in portfolio.columns and 'expected_annual_return' in portfolio.columns and 'weight' in portfolio.columns:
            portfolio['weighted_expected_return'] = portfolio['expected_annual_return'].astype(float) * portfolio['weight']
            existing_columns.append('weighted_expected_return')
        
        portfolio = portfolio[existing_columns]
        return portfolio

    def total_share(self):
        self.optimized_df['total_shares'] = np.divide(
            self.optimized_df['invested_amount'], self.optimized_df['price'].astype(float))
        return self.optimized_df

    def build_portfolio_with_top_stocks(self, df, investing_amount,maximum_stock_price,risk_tolerance):  
        logging.info(f"Building portfolio with {len(df)} stocks initially")
        
        # Check if expected_annual_return exists, if not calculate it
        if 'expected_annual_return' not in df.columns:
            logging.info("expected_annual_return not found, calculating it")
            df = annualReturn.update_with_return_data(df)
        
        # Apply filters with logging
        initial_count = len(df)
        logging.info(f"Initial stock count: {initial_count}")
        
        # Filter by strength
        df_strength = df[df['strength'] > 0]
        logging.info(f"After strength filter: {len(df_strength)} stocks")
        
        # Filter by expected return
        df_return = df_strength[df_strength['expected_annual_return'].astype(float) > 0]
        logging.info(f"After return filter: {len(df_return)} stocks")
        
        # Filter by price
        df_price = df_return[df_return['price'].astype(float) < float(maximum_stock_price)]
        logging.info(f"After price filter: {len(df_price)} stocks")
        
        self.optimized_df = df_price
        
        if len(self.optimized_df) == 0:
            logging.warning("No stocks passed all filters. Relaxing constraints...")
            # Try with just strength filter
            self.optimized_df = df[df['strength'] > 0]
            if len(self.optimized_df) == 0:
                logging.error("No stocks with positive strength found")
                return self.optimized_df
        
        # Apply risk tolerance filter
        self.optimized_df = annualReturn.get_risk_tolerance_data(risk_tolerance, self.optimized_df)
        logging.info(f"After risk tolerance filter: {len(self.optimized_df)} stocks")
        
        # If no stocks passed risk filter, try with all stocks
        if len(self.optimized_df) == 0:
            logging.warning("No stocks passed risk tolerance filter. Using all stocks with positive strength.")
            self.optimized_df = df[df['strength'] > 0]
            logging.info(f"Using all stocks with positive strength: {len(self.optimized_df)} stocks")
        
        # Take top 5 stocks
        self.optimized_df = optimization.calculate_weighted_expected_return(self.optimized_df.head(5))
        logging.info(f"After optimization: {len(self.optimized_df)} stocks")
        
        # Calculate portfolio values
        self.optimized_df = self.calculate_portfolio_value_and_share(investing_amount)
        logging.info(f"Final portfolio: {len(self.optimized_df)} stocks")
        
        return self.optimized_df
    
    def calculate_portfolio_value_distribution(self, investing_amount):
        self.optimized_df['invested_amount'] = np.multiply(
        self.optimized_df['weight'].astype(float), float(investing_amount))
    

    def calculate_portfolio_return(self,df):
        # Check if weighted_expected_return exists, if not calculate it
        if 'weighted_expected_return' not in df.columns:
            if 'expected_annual_return' in df.columns and 'weight' in df.columns:
                df['weighted_expected_return'] = df['expected_annual_return'].astype(float) * df['weight']
            else:
                logging.warning("Cannot calculate portfolio return: missing required columns")
                return 0.0
        
        porfolio_return = df['weighted_expected_return']
        porfolio_return = round(porfolio_return.sum(),3)
        return porfolio_return*100
    
    def calculate_portfolio_risk(self,df):
        portfolio_risk =  df['expected_annual_risk'].astype(float) * df['weight']
        portfolio_risk = portfolio_risk.round(3)
        portfolio_risk = portfolio_risk.sum()
        return portfolio_risk*100

    def save_portfolio_data(self,df,user_id):
        """Save portfolio data to Redis"""
        try:
            # Prepare the data for saving
            new_df = df.drop(columns=['Ticker'])
            new_df = new_df.apply(pd.to_numeric)
            final_df = pd.concat([df['Ticker'],new_df], axis=1)
            final_df['user_id'] = user_id
            
            # Save to Redis using the new data manager
            portfolio_id = redis_manager.save_portfolio(user_id, final_df)
            if portfolio_id:
                # Refresh portfolio list to update internal state
                self.get_portfolios_by_user_id(user_id)
                # Clear the built portfolio after saving
                self.clear_built_portfolio()
                try:
                    flash('Portfolio saved successfully!', 'success')
                except RuntimeError:
                    # Running outside Flask context (e.g., in tests)
                    print('Portfolio saved successfully!')
                return True
            else:
                try:
                    flash('Failed to save portfolio. Please try again.', 'error')
                except RuntimeError:
                    print('Failed to save portfolio. Please try again.')
                return False
        except Exception as e:
            logging.error(f"Error saving portfolio: {e}")
            try:
                flash('Error saving portfolio. Please try again.', 'error')
            except RuntimeError:
                print(f'Error saving portfolio: {e}')
            return False

    def delete_portfolio(self, portfolio_id: str, user_id: str) -> bool:
        """Delete a portfolio by ID"""
        try:
            success = redis_manager.delete_portfolio(portfolio_id, user_id)
            if success:
                try:
                    flash('Portfolio deleted successfully!', 'success')
                except RuntimeError:
                    print('Portfolio deleted successfully!')
                # Refresh portfolio list
                self.get_portfolios_by_user_id(user_id)
                # Clear the built portfolio to prevent stale data
                self.clear_built_portfolio()
                return True
            else:
                try:
                    flash('Failed to delete portfolio. Please try again.', 'error')
                except RuntimeError:
                    print('Failed to delete portfolio. Please try again.')
                return False
        except Exception as e:
            logging.error(f"Error deleting portfolio: {e}")
            try:
                flash('Error deleting portfolio. Please try again.', 'error')
            except RuntimeError:
                print(f'Error deleting portfolio: {e}')
            return False

    def clear_built_portfolio(self):
        """Clear the built portfolio from memory"""
        self.optimized_df = pd.DataFrame()
        logging.info("Built portfolio cleared from memory")

    def get_portfolios_by_user_id(self,user_id):
        """Get portfolios by user ID from Redis"""
        portfolios = redis_manager.get_portfolios_by_user_id(user_id)
        if portfolios:
            # Convert to the format expected by the application with portfolio metadata
            portfolio_records = []
            for portfolio in portfolios:
                if 'data' in portfolio:
                    # Create portfolio object with data property as expected by frontend
                    portfolio_obj = {
                        'data': portfolio['data'],
                        'portfolio_id': portfolio.get('portfolio_id', ''),
                        'created_at': portfolio.get('created_at', ''),
                        'count': portfolio.get('count', 0)
                    }
                    portfolio_records.append(portfolio_obj)
            self.portfolio_list = portfolio_records
            return portfolio_records
        self.portfolio_list = []
        return []
    
    def get_porfolio(self):
        return self.portfolio_list

    def get_build_porfolio(self):
        return self.optimized_df

    def build_portfolio_with_advanced_optimization(self, df, investing_amount, maximum_stock_price, risk_tolerance, method='markowitz'):
        """
        Build portfolio using advanced optimization algorithms
        """
        logging.info(f"Building advanced portfolio with {len(df)} stocks using {method} method")
        
        # Check if expected_annual_return exists, if not calculate it
        if 'expected_annual_return' not in df.columns:
            logging.info("expected_annual_return not found, calculating it")
            df = annualReturn.update_with_return_data(df)
        
        # Apply initial filters
        initial_count = len(df)
        logging.info(f"Initial stock count: {initial_count}")
        
        # Filter by strength
        df_strength = df[df['strength'] > 0]
        logging.info(f"After strength filter: {len(df_strength)} stocks")
        
        # Filter by expected return
        df_return = df_strength[df_strength['expected_annual_return'].astype(float) > 0]
        logging.info(f"After return filter: {len(df_return)} stocks")
        
        # Filter by price
        df_price = df_return[df_return['price'].astype(float) < float(maximum_stock_price)]
        logging.info(f"After price filter: {len(df_price)} stocks")
        
        # Apply risk tolerance filter
        df_risk = annualReturn.get_risk_tolerance_data(risk_tolerance, df_price)
        logging.info(f"After risk tolerance filter: {len(df_risk)} stocks")
        
        # If no stocks passed risk filter, use all stocks with positive strength
        if len(df_risk) == 0:
            logging.warning("No stocks passed risk tolerance filter. Using all stocks with positive strength.")
            df_risk = df[df['strength'] > 0]
        
        # Take top 10 stocks for optimization (more diversification)
        df_optimize = df_risk.head(10)
        logging.info(f"Optimizing with {len(df_optimize)} stocks")
        
        try:
            # Use advanced optimization
            optimization_result = advanced_optimizer.optimize_portfolio(df_optimize, method=method)
            
            # Create portfolio DataFrame with optimized weights
            self.optimized_df = df_optimize.copy()
            self.optimized_df['weight'] = optimization_result['weights']
            
            # Calculate portfolio values
            self.optimized_df = self.calculate_portfolio_value_and_share(investing_amount)
            
            # Add optimization metrics
            self.optimization_metrics = {
                'method': optimization_result['method'],
                'expected_return': optimization_result['expected_return'],
                'volatility': optimization_result['volatility'],
                'sharpe_ratio': optimization_result['sharpe_ratio']
            }
            
            logging.info(f"Advanced optimization completed. Expected return: {optimization_result['expected_return']:.4f}, "
                        f"Volatility: {optimization_result['volatility']:.4f}, Sharpe: {optimization_result['sharpe_ratio']:.4f}")
            
            return self.optimized_df
            
        except Exception as e:
            logging.error(f"Advanced optimization failed: {e}. Falling back to basic optimization.")
            # Fall back to basic optimization but still set metrics
            fallback_df = self.build_portfolio_with_top_stocks(df, investing_amount, maximum_stock_price, risk_tolerance)
            
            # Set basic metrics for fallback
            if not fallback_df.empty:
                self.optimization_metrics = {
                    'method': 'basic_fallback',
                    'expected_return': self.calculate_portfolio_return(fallback_df) / 100,  # Convert from percentage
                    'volatility': self.calculate_portfolio_risk(fallback_df) / 100,  # Convert from percentage
                    'sharpe_ratio': 0.0  # Basic fallback doesn't calculate Sharpe ratio
                }
            
            return fallback_df
    
    def compare_optimization_methods(self, df, investing_amount, maximum_stock_price, risk_tolerance):
        """
        Compare different optimization methods and return results
        """
        logging.info("Comparing optimization methods")
        
        # Prepare data (same as advanced optimization)
        if 'expected_annual_return' not in df.columns:
            df = annualReturn.update_with_return_data(df)
        
        df_filtered = df[(df['strength'] > 0) & 
                        (df['expected_annual_return'].astype(float) > 0) & 
                        (df['price'].astype(float) < float(maximum_stock_price))]
        
        df_risk = annualReturn.get_risk_tolerance_data(risk_tolerance, df_filtered)
        if len(df_risk) == 0:
            df_risk = df[df['strength'] > 0]
        
        df_optimize = df_risk.head(10)
        
        # Compare methods
        methods = ['markowitz', 'risk_parity', 'max_sharpe', 'hrp']
        results = {}
        
        for method in methods:
            try:
                result = advanced_optimizer.optimize_portfolio(df_optimize, method=method)
                results[method] = result
                logging.info(f"{method}: Return={result['expected_return']:.4f}, Vol={result['volatility']:.4f}, Sharpe={result['sharpe_ratio']:.4f}")
            except Exception as e:
                logging.error(f"Method {method} failed: {e}")
                results[method] = None
        
        return results
    
    def backtest_portfolio(self, df, investing_amount, maximum_stock_price, risk_tolerance):
        """
        Backtest the portfolio strategy
        """
        logging.info("Starting portfolio backtesting")
        
        # Get optimized portfolio
        portfolio_df = self.build_portfolio_with_advanced_optimization(
            df, investing_amount, maximum_stock_price, risk_tolerance
        )
        
        if portfolio_df.empty:
            logging.error("No portfolio data for backtesting")
            return None
        
        # Extract tickers and weights
        tickers = portfolio_df['Ticker'].tolist()
        weights = portfolio_df['weight'].values
        
        # Generate historical data for backtesting
        historical_prices = backtester.generate_historical_data(tickers)
        
        # Define strategies to compare
        strategies = {
            'Equal Weight': np.ones(len(tickers)) / len(tickers),
            'Optimized': weights,
            'Market Cap Weight': np.ones(len(tickers)) / len(tickers)  # Simplified
        }
        
        # Run backtesting
        backtest_results = backtester.compare_strategies(historical_prices, strategies)
        
        # Generate report
        report = backtester.generate_report(backtest_results)
        logging.info("Backtesting completed")
        
        return {
            'results': backtest_results,
            'report': report,
            'portfolio_data': portfolio_df
        }
    
    def get_optimization_metrics(self):
        """
        Get the latest optimization metrics
        """
        return getattr(self, 'optimization_metrics', {})
