import logging
import os
from datetime import datetime

import numpy as np
from flask import Blueprint, request, jsonify, current_app

from services.portfolio import portfolio as buildPortfolio
from services.strengthCalculator import StrengthCalculator, CanonicalDataUnavailable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

buildPortfolio = buildPortfolio()
strengthCalculator = StrengthCalculator()


@main.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({
        'status': 'healthy',
        'service': 'stocknity-analytics',
        'timestamp': datetime.utcnow().isoformat()
    })


@main.route('/', methods=['GET'])
def api_root():
    return jsonify({'service': 'stocknity-analytics', 'status': 'ok'})


@main.route('/api/portfolio', methods=['GET', 'POST'])
def api_portfolio():
    if request.method == 'POST':
        try:
            data = request.get_json() or {}
            btn = data.get('btn', '')

            if btn == 'Build':
                strength_df = strengthCalculator.calculate_strength_value(
                    sector=data.get('sector'),
                    index=data.get('index'),
                    stock_type=data.get('stock_type')
                )
                portfolio = buildPortfolio.build_portfolio_with_top_stocks(
                    strength_df,
                    data.get('investing_amount'),
                    data.get('max_stock_price'),
                    data.get('risk_tolerance')
                )
            elif btn == 'Optimize':
                strength_df = strengthCalculator.calculate_strength_value(
                    sector='Any', index='S&P 500', stock_type=data.get('stock_type')
                )
                selected_stocks = list(set(data.get('stock[]', [])))
                portfolio = buildPortfolio.build_portfolio_from_user_input_tickers(
                    strength_df,
                    selected_stocks,
                    data.get('expected_return_value'),
                    data.get('investing_amount'),
                    data.get('risk_tolerance')
                )
            elif btn == 'Save Portfolio':
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': f'Unknown action: {btn}'})

            if not portfolio.empty:
                return jsonify({'success': True, 'data': portfolio.to_dict('records')})
            return jsonify({'success': False, 'error': 'Failed to build portfolio'})

        except CanonicalDataUnavailable as e:
            current_app.logger.warning(f"Canonical data unavailable: {e}")
            return jsonify({
                'success': False,
                'error': 'Market data not yet available',
                'detail': str(e)
            }), 503
        except Exception as e:
            current_app.logger.error(f"Portfolio error: {e}")
            return jsonify({'success': False, 'error': str(e)})

    return jsonify({'message': 'Portfolio API'})


@main.route('/api/clear-built-portfolio', methods=['POST'])
def api_clear_built_portfolio():
    buildPortfolio.clear_built_portfolio()
    return jsonify({'success': True})


@main.route('/api/portfolio/advanced', methods=['POST'])
def api_advanced_portfolio():
    try:
        data = request.get_json() if request.is_json else request.form
        method = data.get('method', 'markowitz')
        investing_amount = float(data.get('investing_amount', 10000))
        max_stock_price = float(data.get('max_stock_price', 100))
        risk_tolerance = data.get('risk_tolerance', 'Medium')
        sector = data.get('sector', 'Any')
        index = data.get('index', 'S&P 500')
        stock_type = data.get('stock_type', 'Value')

        strength_df = strengthCalculator.calculate_strength_value(stock_type, sector, index)
        if strength_df.empty:
            return jsonify({'success': False, 'error': 'No strength data available'})

        portfolio_df = buildPortfolio.build_portfolio_with_advanced_optimization(
            strength_df, investing_amount, max_stock_price, risk_tolerance, method
        )
        if portfolio_df.empty:
            return jsonify({'success': False, 'error': 'Failed to build portfolio'})

        metrics = buildPortfolio.get_optimization_metrics()
        return jsonify({
            'success': True,
            'data': portfolio_df.to_dict('records'),
            'metrics': metrics,
            'method': method
        })

    except CanonicalDataUnavailable as e:
        current_app.logger.warning(f"Canonical data unavailable: {e}")
        return jsonify({
            'success': False,
            'error': 'Market data not yet available',
            'detail': str(e)
        }), 503
    except Exception as e:
        current_app.logger.error(f"Advanced portfolio error: {e}")
        return jsonify({'success': False, 'error': str(e)})


@main.route('/api/portfolio/compare-methods', methods=['POST'])
def api_compare_optimization_methods():
    try:
        data = request.get_json() if request.is_json else request.form
        investing_amount = float(data.get('investing_amount', 10000))
        max_stock_price = float(data.get('max_stock_price', 100))
        risk_tolerance = data.get('risk_tolerance', 'Medium')
        sector = data.get('sector', 'Any')
        index = data.get('index', 'S&P 500')
        stock_type = data.get('stock_type', 'Value')

        strength_df = strengthCalculator.calculate_strength_value(stock_type, sector, index)
        if strength_df.empty:
            return jsonify({'success': False, 'error': 'No strength data available'})

        comparison_results = buildPortfolio.compare_optimization_methods(
            strength_df, investing_amount, max_stock_price, risk_tolerance
        )

        formatted = {}
        for method, result in comparison_results.items():
            if result:
                weights = result['weights']
                tickers = result['tickers']
                top_indices = np.argsort(weights)[-3:][::-1]
                formatted[method] = {
                    'expected_return': result['expected_return'],
                    'volatility': result['volatility'],
                    'sharpe_ratio': result['sharpe_ratio'],
                    'method': result['method'],
                    'top_holdings': [
                        {'ticker': tickers[i], 'weight': float(weights[i])}
                        for i in top_indices
                    ]
                }

        return jsonify({'success': True, 'results': formatted})

    except CanonicalDataUnavailable as e:
        current_app.logger.warning(f"Canonical data unavailable: {e}")
        return jsonify({
            'success': False,
            'error': 'Market data not yet available',
            'detail': str(e)
        }), 503
    except Exception as e:
        current_app.logger.error(f"Compare methods error: {e}")
        return jsonify({'success': False, 'error': str(e)})


@main.route('/api/portfolio/backtest', methods=['POST'])
def api_portfolio_backtest():
    try:
        data = request.get_json() if request.is_json else request.form
        investing_amount = float(data.get('investing_amount', 10000))
        max_stock_price = float(data.get('max_stock_price', 100))
        risk_tolerance = data.get('risk_tolerance', 'Medium')
        sector = data.get('sector', 'Any')
        index = data.get('index', 'S&P 500')
        stock_type = data.get('stock_type', 'Value')

        strength_df = strengthCalculator.calculate_strength_value(stock_type, sector, index)
        if strength_df.empty:
            return jsonify({'success': False, 'error': 'No strength data available'})

        backtest_results = buildPortfolio.backtest_portfolio(
            strength_df, investing_amount, max_stock_price, risk_tolerance
        )
        if not backtest_results:
            return jsonify({'success': False, 'error': 'Backtesting failed'})

        formatted = {}
        for strategy, result in backtest_results['results'].items():
            if result:
                m = result['metrics']
                formatted[strategy] = {
                    'total_return': m['total_return'],
                    'annualized_return': m['annualized_return'],
                    'volatility': m['volatility'],
                    'sharpe_ratio': m['sharpe_ratio'],
                    'max_drawdown': m['max_drawdown'],
                    'var_95': m['var_95'],
                    'cvar_95': m['cvar_95'],
                    'calmar_ratio': m['calmar_ratio'],
                    'information_ratio': m['information_ratio']
                }

        return jsonify({
            'success': True,
            'backtest_results': formatted,
            'report': backtest_results['report'],
            'portfolio_data': backtest_results['portfolio_data'].to_dict('records')
        })

    except CanonicalDataUnavailable as e:
        current_app.logger.warning(f"Canonical data unavailable: {e}")
        return jsonify({
            'success': False,
            'error': 'Market data not yet available',
            'detail': str(e)
        }), 503
    except Exception as e:
        current_app.logger.error(f"Backtest error: {e}")
        return jsonify({'success': False, 'error': str(e)})


@main.route('/api/ai/sentiment/<ticker>', methods=['GET'])
def get_ai_sentiment(ticker):
    try:
        import asyncio
        from services.ai_sentiment_analyzer import ai_sentiment_service

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            ai_sentiment_service.get_comprehensive_sentiment(ticker.upper().strip())
        )
        loop.close()
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Sentiment error for {ticker}: {e}")
        return jsonify({'error': str(e), 'ticker': ticker}), 500


@main.route('/api/ai/sentiment/<ticker>/trend', methods=['GET'])
def get_sentiment_trend(ticker):
    try:
        import asyncio
        from services.ai_sentiment_analyzer import ai_sentiment_service

        days = request.args.get('days', 7, type=int)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            ai_sentiment_service.get_sentiment_trend(ticker.upper(), days)
        )
        loop.close()
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Sentiment trend error for {ticker}: {e}")
        return jsonify({'error': str(e), 'ticker': ticker}), 500
