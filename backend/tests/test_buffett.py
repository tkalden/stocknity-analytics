"""
Tests for Warren Buffett Value Investing Strategy

This module tests the WarrenBuffettStrategy implementation.
"""

import pytest
from backend.services.gurus.buffett import WarrenBuffettStrategy


class TestBuffettInitialization:
    """Test Buffett strategy initialization."""
    
    def test_initialization(self):
        """Buffett strategy initializes with correct attributes."""
        buffett = WarrenBuffettStrategy()
        
        assert buffett.name == "Warren Buffett"
        assert buffett.description == "Value investing with focus on quality and economic moat"
        assert buffett.strategy_type == "value"
        assert buffett.risk_level == "low"
    
    def test_key_metrics(self):
        """Buffett focuses on value investing metrics."""
        buffett = WarrenBuffettStrategy()
        metrics = buffett.get_key_metrics()
        
        assert metrics == ['ROE', 'Net Margin', 'Debt/Equity', 'Earnings Growth', 'P/E Ratio']


class TestBuffettScoring:
    """Test Buffett scoring logic."""
    
    def test_perfect_score_quality_company(self):
        """Wonderful company scores very high."""
        buffett = WarrenBuffettStrategy()
        
        # Perfect Buffett company
        stock_data = {
            'ticker': 'AAPL',
            'current_price': 150.00,
            'eps': 6.00,
            'roe': 0.35,  # 35% ROE (exceptional)
            'net_margin': 0.25,  # 25% margin (excellent)
            'debt_to_equity': 0.3,  # Low debt
            'earnings_growth': 0.15,  # 15% growth
            'pe_ratio': 20.0,
            'industry_pe': 25.0  # Trading below industry
        }
        
        result = buffett.evaluate_stock(stock_data)
        
        # Should get maximum points in all categories
        assert result['score'] == 100  # 30 + 20 + 20 + 15 + 15
        assert result['rating'] == 'excellent'
        assert result['key_metrics']['roe_score'] == 30
        assert result['key_metrics']['margin_score'] == 20
        assert result['key_metrics']['debt_score'] == 20
        assert result['key_metrics']['growth_score'] == 15
        assert result['key_metrics']['valuation_score'] == 15
    
    def test_good_quality_company(self):
        """Good quality company scores well."""
        buffett = WarrenBuffettStrategy()
        
        stock_data = {
            'ticker': 'MSFT',
            'current_price': 300.00,
            'eps': 10.00,
            'roe': 0.18,  # 18% ROE (good)
            'net_margin': 0.18,  # 18% margin (strong)
            'debt_to_equity': 0.6,  # Moderate debt
            'earnings_growth': 0.08,  # 8% growth
            'pe_ratio': 28.0,
            'industry_pe': 26.0  # Slightly above industry
        }
        
        result = buffett.evaluate_stock(stock_data)
        
        # Should get good but not perfect scores
        assert 60 <= result['score'] < 80
        assert result['rating'] == 'good'
        assert result['key_metrics']['roe_score'] == 20  # 15-20% ROE
        assert result['key_metrics']['margin_score'] == 15  # 15-20% margin
        assert result['key_metrics']['debt_score'] == 10  # D/E 0.5-1.0
    
    def test_poor_quality_company(self):
        """Poor quality company scores low."""
        buffett = WarrenBuffettStrategy()
        
        stock_data = {
            'ticker': 'POOR',
            'current_price': 50.00,
            'eps': 2.00,
            'roe': 0.08,  # 8% ROE (weak)
            'net_margin': 0.05,  # 5% margin (thin)
            'debt_to_equity': 2.5,  # High debt
            'earnings_growth': 0.02,  # 2% growth
            'pe_ratio': 35.0,
            'industry_pe': 20.0  # Overvalued vs industry
        }
        
        result = buffett.evaluate_stock(stock_data)
        
        # Should score poorly
        assert result['score'] < 40
        assert result['rating'] == 'poor'
        assert result['key_metrics']['roe_score'] == 0  # Below 10% ROE
        assert result['key_metrics']['debt_score'] == 0  # D/E > 1.0


class TestBuffettFairValue:
    """Test Buffett fair value calculation."""
    
    def test_fair_value_high_quality(self):
        """High ROE companies get higher fair value."""
        buffett = WarrenBuffettStrategy()
        
        # High quality: 30% ROE, 15% growth, $6 EPS
        fair_value = buffett._calculate_fair_value(eps=6.00, growth_rate=0.15, roe=0.30)
        
        # fair_pe = 15 * (30/15) = 30 (clamped to max 30)
        # fair_value = 6 * 30 = 180
        assert fair_value == 180.00
    
    def test_fair_value_moderate_quality(self):
        """Moderate quality gets moderate fair value."""
        buffett = WarrenBuffettStrategy()
        
        # Moderate: 15% ROE, 10% growth, $4 EPS
        fair_value = buffett._calculate_fair_value(eps=4.00, growth_rate=0.10, roe=0.15)
        
        # fair_pe = 10 * (15/15) = 10 (at minimum)
        # fair_value = 4 * 10 = 40
        assert fair_value == 40.00
    
    def test_fair_value_low_eps(self):
        """Zero or negative EPS returns zero fair value."""
        buffett = WarrenBuffettStrategy()
        
        assert buffett._calculate_fair_value(eps=0, growth_rate=0.10, roe=0.20) == 0.0
        assert buffett._calculate_fair_value(eps=-1, growth_rate=0.10, roe=0.20) == 0.0
    
    def test_fair_value_clamping(self):
        """Fair P/E is clamped between 10 and 30."""
        buffett = WarrenBuffettStrategy()
        
        # Very high growth/ROE should clamp to 30
        fair_value_high = buffett._calculate_fair_value(eps=5.00, growth_rate=0.50, roe=0.50)
        assert fair_value_high == 150.00  # 5 * 30 (clamped)
        
        # Very low growth/ROE should clamp to 10
        fair_value_low = buffett._calculate_fair_value(eps=5.00, growth_rate=0.01, roe=0.05)
        assert fair_value_low == 50.00  # 5 * 10 (clamped)


class TestBuffettRecommendations:
    """Test recommendation logic."""
    
    def test_strong_buy_recommendation(self):
        """High quality + good price = strong buy."""
        buffett = WarrenBuffettStrategy()
        
        stock_data = {
            'ticker': 'BUY',
            'current_price': 80.00,  # Below fair value
            'eps': 6.00,
            'roe': 0.30,
            'net_margin': 0.25,
            'debt_to_equity': 0.3,
            'earnings_growth': 0.15,
            'pe_ratio': 13.33,  # 80/6
            'industry_pe': 20.0
        }
        
        result = buffett.evaluate_stock(stock_data)
        
        # High score + margin of safety = strong buy
        assert result['score'] >= 80
        assert result['margin_of_safety'] > 0.15
        assert result['recommendation'] == 'strong_buy'
    
    def test_hold_recommendation_fair_price(self):
        """Good company at fair price = hold."""
        buffett = WarrenBuffettStrategy()
        
        stock_data = {
            'ticker': 'HOLD',
            'current_price': 75.00,  # At fair value (will calculate ~70-75 fair value)
            'eps': 6.00,
            'roe': 0.17,  # 17% ROE (good, not exceptional) -> 20 points
            'net_margin': 0.16,  # 16% margin (strong) -> 15 points
            'debt_to_equity': 0.6,  # Moderate debt -> 10 points
            'earnings_growth': 0.08,  # 8% growth -> 10 points
            'pe_ratio': 12.5,  # 75/6
            'industry_pe': 22.0  # Below industry -> 15 points
        }
        
        result = buffett.evaluate_stock(stock_data)
        
        # Good score: 20 + 15 + 10 + 10 + 15 = 70
        # Fair value: eps(6) * fair_pe(8 * 1.13 = ~9, clamped to 10) = 60
        # Margin of safety: (60-75)/60 = -25% (slightly overvalued but not terrible)
        assert 60 <= result['score'] < 80
        # With good score but negative margin, should be hold
        assert result['recommendation'] in ['hold', 'sell']  # Could be sell if >20% overvalued
    
    def test_sell_recommendation_poor_quality(self):
        """Poor quality company = sell."""
        buffett = WarrenBuffettStrategy()
        
        stock_data = {
            'ticker': 'SELL',
            'current_price': 50.00,
            'eps': 2.00,
            'roe': 0.05,
            'net_margin': 0.04,
            'debt_to_equity': 3.0,
            'earnings_growth': 0.01,
            'pe_ratio': 25.0,
            'industry_pe': 20.0
        }
        
        result = buffett.evaluate_stock(stock_data)
        
        # Low score = sell
        assert result['score'] < 40
        assert result['recommendation'] == 'sell'


class TestBuffettInsights:
    """Test insight generation."""
    
    def test_insight_wonderful_company(self):
        """Wonderful company gets enthusiastic insight."""
        buffett = WarrenBuffettStrategy()
        
        stock_data = {
            'ticker': 'AAPL',
            'current_price': 100.00,
            'eps': 6.00,
            'roe': 0.30,
            'net_margin': 0.25,
            'debt_to_equity': 0.3,
            'earnings_growth': 0.15,
            'pe_ratio': 16.67,
            'industry_pe': 25.0
        }
        
        result = buffett.evaluate_stock(stock_data)
        insight = buffett.generate_insight(stock_data, result)
        
        # Should be enthusiastic for wonderful company
        assert 'wonderful company' in insight.lower()
        assert 'economic moat' in insight.lower()
        assert 'AAPL' in insight
        assert result['score'] >= 80
    
    def test_insight_solid_company(self):
        """Solid company gets positive but measured insight."""
        buffett = WarrenBuffettStrategy()
        
        stock_data = {
            'ticker': 'MSFT',
            'current_price': 300.00,
            'eps': 10.00,
            'roe': 0.18,
            'net_margin': 0.18,
            'debt_to_equity': 0.6,
            'earnings_growth': 0.08,
            'pe_ratio': 30.0,
            'industry_pe': 28.0
        }
        
        result = buffett.evaluate_stock(stock_data)
        insight = buffett.generate_insight(stock_data, result)
        
        # Should be positive but measured
        assert 'solid company' in insight.lower() or 'good fundamentals' in insight.lower()
        assert 'MSFT' in insight
    
    def test_insight_poor_company(self):
        """Poor company gets negative insight."""
        buffett = WarrenBuffettStrategy()
        
        stock_data = {
            'ticker': 'POOR',
            'current_price': 50.00,
            'eps': 2.00,
            'roe': 0.05,
            'net_margin': 0.04,
            'debt_to_equity': 3.0,
            'earnings_growth': 0.01,
            'pe_ratio': 25.0,
            'industry_pe': 20.0
        }
        
        result = buffett.evaluate_stock(stock_data)
        insight = buffett.generate_insight(stock_data, result)
        
        # Should recommend passing
        assert 'pass' in insight.lower() or "doesn't meet" in insight.lower()
        assert 'POOR' in insight


class TestBuffettEdgeCases:
    """Test edge cases and missing data."""
    
    def test_missing_data_defaults(self):
        """Strategy handles missing data gracefully."""
        buffett = WarrenBuffettStrategy()
        
        # Minimal data
        stock_data = {
            'ticker': 'TEST',
            'current_price': 100.00
        }
        
        result = buffett.evaluate_stock(stock_data)
        
        # Should not crash, returns low score for missing data
        assert 'score' in result
        assert result['score'] >= 0
        assert 'rating' in result
        assert 'fair_value' in result
    
    def test_zero_values(self):
        """Strategy handles zero values."""
        buffett = WarrenBuffettStrategy()
        
        stock_data = {
            'ticker': 'ZERO',
            'current_price': 100.00,
            'eps': 0.0,
            'roe': 0.0,
            'net_margin': 0.0,
            'debt_to_equity': 0.0,
            'earnings_growth': 0.0,
            'pe_ratio': 0.0
        }
        
        result = buffett.evaluate_stock(stock_data)
        
        # Should handle zeros gracefully
        assert result['fair_value'] == 0.0
        assert result['score'] >= 0  # At least gets points for zero debt


class TestBuffettEvaluation:
    """Integration tests for complete evaluation flow."""
    
    def test_complete_evaluation_structure(self):
        """Evaluation returns all required fields."""
        buffett = WarrenBuffettStrategy()
        
        stock_data = {
            'ticker': 'TEST',
            'current_price': 150.00,
            'eps': 6.00,
            'roe': 0.25,
            'net_margin': 0.20,
            'debt_to_equity': 0.4,
            'earnings_growth': 0.12,
            'pe_ratio': 25.0,
            'industry_pe': 28.0
        }
        
        result = buffett.evaluate_stock(stock_data)
        
        # Verify all required fields present
        assert 'score' in result
        assert 'rating' in result
        assert 'recommendation' in result
        assert 'reasoning' in result
        assert 'key_metrics' in result
        assert 'fair_value' in result
        assert 'margin_of_safety' in result
        
        # Verify types
        assert isinstance(result['score'], int)
        assert isinstance(result['rating'], str)
        assert isinstance(result['recommendation'], str)
        assert isinstance(result['reasoning'], str)
        assert isinstance(result['key_metrics'], dict)
        assert isinstance(result['fair_value'], float)
        assert isinstance(result['margin_of_safety'], float)
        
        # Verify score is in valid range
        assert 0 <= result['score'] <= 100
    
    def test_reasoning_contains_analysis(self):
        """Reasoning includes specific analysis."""
        buffett = WarrenBuffettStrategy()
        
        stock_data = {
            'ticker': 'AAPL',
            'current_price': 150.00,
            'eps': 6.00,
            'roe': 0.30,
            'net_margin': 0.22,
            'debt_to_equity': 0.4,
            'earnings_growth': 0.12,
            'pe_ratio': 25.0,
            'industry_pe': 28.0
        }
        
        result = buffett.evaluate_stock(stock_data)
        
        # Reasoning should mention the ticker and key metrics
        assert 'AAPL' in result['reasoning']
        assert 'ROE' in result['reasoning'] or 'moat' in result['reasoning'].lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

