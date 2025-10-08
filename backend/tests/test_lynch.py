"""
Tests for Peter Lynch GARP Strategy

This module tests the PeterLynchStrategy implementation.
"""

import pytest
from backend.services.gurus.lynch import PeterLynchStrategy


class TestLynchInitialization:
    """Test Lynch strategy initialization."""
    
    def test_initialization(self):
        """Lynch strategy initializes with correct attributes."""
        lynch = PeterLynchStrategy()
        
        assert lynch.name == "Peter Lynch"
        assert lynch.description == "Growth at reasonable price - find growing companies with good valuations"
        assert lynch.strategy_type == "growth"
        assert lynch.risk_level == "medium"
    
    def test_key_metrics(self):
        """Lynch focuses on growth metrics."""
        lynch = PeterLynchStrategy()
        metrics = lynch.get_key_metrics()
        
        assert metrics == ['PEG Ratio', 'Revenue Growth', 'EPS Growth', 'P/E Ratio', 'Sector']
    
    def test_familiar_sectors(self):
        """Lynch has defined familiar sectors."""
        lynch = PeterLynchStrategy()
        
        assert 'Technology' in lynch.FAMILIAR_SECTORS
        assert 'Healthcare' in lynch.FAMILIAR_SECTORS
        assert 'Retail' in lynch.FAMILIAR_SECTORS


class TestPEGCalculation:
    """Test PEG ratio calculation."""
    
    def test_peg_calculation_normal(self):
        """Calculate PEG ratio with normal values."""
        lynch = PeterLynchStrategy()
        
        # P/E of 30, growth of 30% = PEG of 1.0
        peg = lynch._calculate_peg_ratio(pe_ratio=30.0, earnings_growth=0.30)
        assert peg == 1.0
    
    def test_peg_calculation_undervalued(self):
        """Low PEG indicates undervaluation."""
        lynch = PeterLynchStrategy()
        
        # P/E of 20, growth of 40% = PEG of 0.5
        peg = lynch._calculate_peg_ratio(pe_ratio=20.0, earnings_growth=0.40)
        assert peg == 0.5
    
    def test_peg_calculation_overvalued(self):
        """High PEG indicates overvaluation."""
        lynch = PeterLynchStrategy()
        
        # P/E of 60, growth of 20% = PEG of 3.0
        peg = lynch._calculate_peg_ratio(pe_ratio=60.0, earnings_growth=0.20)
        assert peg == 3.0
    
    def test_peg_zero_growth(self):
        """Zero or negative growth returns 0 PEG."""
        lynch = PeterLynchStrategy()
        
        assert lynch._calculate_peg_ratio(pe_ratio=30.0, earnings_growth=0.0) == 0.0
        assert lynch._calculate_peg_ratio(pe_ratio=30.0, earnings_growth=-0.10) == 0.0
    
    def test_peg_zero_pe(self):
        """Zero or negative P/E returns 0 PEG."""
        lynch = PeterLynchStrategy()
        
        assert lynch._calculate_peg_ratio(pe_ratio=0.0, earnings_growth=0.20) == 0.0
        assert lynch._calculate_peg_ratio(pe_ratio=-10.0, earnings_growth=0.20) == 0.0


class TestLynchScoring:
    """Test Lynch scoring logic."""
    
    def test_perfect_growth_stock(self):
        """Perfect 10-bagger candidate scores very high."""
        lynch = PeterLynchStrategy()
        
        stock_data = {
            'ticker': 'GROW',
            'current_price': 100.00,
            'eps': 5.00,
            'pe_ratio': 20.0,  # P/E of 20
            'earnings_growth': 0.40,  # 40% growth -> PEG = 20/40 = 0.5
            'revenue_growth': 0.30,  # 30% revenue growth
            'sector': 'Technology'
        }
        
        result = lynch.evaluate_stock(stock_data)
        
        # PEG < 1: 35, Revenue > 20%: 30, EPS > 25%: 20, Familiar sector: 15 = 100
        assert result['score'] == 100
        assert result['rating'] == 'excellent'
        assert result['key_metrics']['peg_ratio'] == 0.5
        assert result['key_metrics']['peg_score'] == 35
        assert result['key_metrics']['revenue_score'] == 30
        assert result['key_metrics']['eps_growth_score'] == 20
        assert result['key_metrics']['understandability_score'] == 15
    
    def test_good_growth_stock(self):
        """Good growth stock scores well."""
        lynch = PeterLynchStrategy()
        
        stock_data = {
            'ticker': 'GOOD',
            'current_price': 150.00,
            'eps': 6.00,
            'pe_ratio': 28.0,  # Changed to get PEG < 1.5
            'earnings_growth': 0.20,  # 20% growth -> PEG = 28/20 = 1.4
            'revenue_growth': 0.18,  # 18% revenue growth
            'sector': 'Healthcare'
        }
        
        result = lynch.evaluate_stock(stock_data)
        
        # PEG 1.4 (< 1.5): 25, Revenue > 15%: 20, EPS > 15%: 15, Familiar: 15 = 75
        assert result['score'] == 75
        assert result['rating'] == 'good'
    
    def test_poor_growth_stock(self):
        """Slow growth at high price scores poorly."""
        lynch = PeterLynchStrategy()
        
        stock_data = {
            'ticker': 'POOR',
            'current_price': 80.00,
            'eps': 2.00,
            'pe_ratio': 40.0,
            'earnings_growth': 0.08,  # 8% growth -> PEG = 40/8 = 5.0
            'revenue_growth': 0.05,  # 5% revenue growth
            'sector': 'Utilities'  # Not in familiar sectors
        }
        
        result = lynch.evaluate_stock(stock_data)
        
        # PEG > 2: 0, Revenue < 10%: 0, EPS < 10%: 0, Unfamiliar: 0 = 0
        assert result['score'] == 0
        assert result['rating'] == 'poor'


class TestLynchFairValue:
    """Test Lynch fair value calculation."""
    
    def test_fair_value_high_growth(self):
        """High growth companies get higher fair values."""
        lynch = PeterLynchStrategy()
        
        # 40% growth, $5 EPS
        # fair_pe = 1.5 * 40 = 60, clamped to 50
        # fair_value = 5 * 50 = 250
        fair_value = lynch._calculate_fair_value(eps=5.00, earnings_growth=0.40)
        assert fair_value == 250.00
    
    def test_fair_value_moderate_growth(self):
        """Moderate growth gets moderate fair value."""
        lynch = PeterLynchStrategy()
        
        # 20% growth, $4 EPS
        # fair_pe = 1.5 * 20 = 30
        # fair_value = 4 * 30 = 120
        fair_value = lynch._calculate_fair_value(eps=4.00, earnings_growth=0.20)
        assert fair_value == 120.00
    
    def test_fair_value_low_growth(self):
        """Low growth gets clamped to minimum P/E."""
        lynch = PeterLynchStrategy()
        
        # 5% growth, $3 EPS
        # fair_pe = 1.5 * 5 = 7.5, clamped to 10
        # fair_value = 3 * 10 = 30
        fair_value = lynch._calculate_fair_value(eps=3.00, earnings_growth=0.05)
        assert fair_value == 30.00
    
    def test_fair_value_zero_eps(self):
        """Zero or negative EPS returns zero fair value."""
        lynch = PeterLynchStrategy()
        
        assert lynch._calculate_fair_value(eps=0.0, earnings_growth=0.20) == 0.0
        assert lynch._calculate_fair_value(eps=-1.0, earnings_growth=0.20) == 0.0
    
    def test_fair_value_zero_growth(self):
        """Zero or negative growth returns zero fair value."""
        lynch = PeterLynchStrategy()
        
        assert lynch._calculate_fair_value(eps=5.0, earnings_growth=0.0) == 0.0
        assert lynch._calculate_fair_value(eps=5.0, earnings_growth=-0.10) == 0.0


class TestLynchRecommendations:
    """Test recommendation logic."""
    
    def test_strong_buy_10bagger(self):
        """Perfect growth stock = strong buy."""
        lynch = PeterLynchStrategy()
        
        stock_data = {
            'ticker': 'TENBAG',
            'current_price': 50.00,  # Below fair value
            'eps': 3.00,
            'pe_ratio': 16.67,  # 50/3
            'earnings_growth': 0.35,  # 35% growth
            'revenue_growth': 0.28,
            'sector': 'Technology'
        }
        
        result = lynch.evaluate_stock(stock_data)
        
        # High score + good margin = strong buy
        assert result['score'] >= 80
        assert result['recommendation'] in ['strong_buy', 'buy']
    
    def test_hold_fair_price(self):
        """Good stock at fair price = hold or buy."""
        lynch = PeterLynchStrategy()
        
        stock_data = {
            'ticker': 'HOLD',
            'current_price': 100.00,
            'eps': 4.00,
            'pe_ratio': 25.0,
            'earnings_growth': 0.18,  # 18% growth
            'revenue_growth': 0.16,
            'sector': 'Consumer Cyclical'
        }
        
        result = lynch.evaluate_stock(stock_data)
        
        # Decent score
        assert 60 <= result['score'] < 80
        assert result['recommendation'] in ['hold', 'buy']
    
    def test_sell_overpriced_growth(self):
        """Overpriced slow growth = sell."""
        lynch = PeterLynchStrategy()
        
        stock_data = {
            'ticker': 'SELL',
            'current_price': 120.00,
            'eps': 2.00,
            'pe_ratio': 60.0,
            'earnings_growth': 0.08,  # 8% growth -> PEG = 7.5
            'revenue_growth': 0.06,
            'sector': 'Unknown'
        }
        
        result = lynch.evaluate_stock(stock_data)
        
        # Poor score = sell
        assert result['score'] < 40
        assert result['recommendation'] == 'sell'


class TestLynchInsights:
    """Test insight generation."""
    
    def test_insight_10bagger(self):
        """10-bagger candidate gets enthusiastic insight."""
        lynch = PeterLynchStrategy()
        
        stock_data = {
            'ticker': 'AMZN',
            'current_price': 100.00,
            'eps': 4.00,
            'pe_ratio': 25.0,
            'earnings_growth': 0.40,
            'revenue_growth': 0.30,
            'sector': 'Technology'
        }
        
        result = lynch.evaluate_stock(stock_data)
        insight = lynch.generate_insight(stock_data, result)
        
        # Should mention 10-bagger and PEG ratio
        assert '10-bagger' in insight.lower() or 'big winner' in insight.lower()
        assert 'PEG' in insight or 'peg' in insight.lower()
        assert 'AMZN' in insight
    
    def test_insight_solid_growth(self):
        """Solid growth gets positive insight."""
        lynch = PeterLynchStrategy()
        
        stock_data = {
            'ticker': 'MSFT',
            'current_price': 200.00,
            'eps': 8.00,
            'pe_ratio': 25.0,
            'earnings_growth': 0.18,
            'revenue_growth': 0.15,
            'sector': 'Technology'
        }
        
        result = lynch.evaluate_stock(stock_data)
        insight = lynch.generate_insight(stock_data, result)
        
        # Should be positive
        assert 'solid' in insight.lower() or 'good' in insight.lower()
        assert 'MSFT' in insight
    
    def test_insight_overpriced(self):
        """Overpriced stock gets cautious insight."""
        lynch = PeterLynchStrategy()
        
        stock_data = {
            'ticker': 'OVERPRICE',
            'current_price': 150.00,
            'eps': 2.00,
            'pe_ratio': 75.0,
            'earnings_growth': 0.10,
            'revenue_growth': 0.08,
            'sector': 'Mining'
        }
        
        result = lynch.evaluate_stock(stock_data)
        insight = lynch.generate_insight(stock_data, result)
        
        # Should recommend passing
        assert 'pass' in insight.lower() or 'wait' in insight.lower()
        assert 'OVERPRICE' in insight


class TestLynchEdgeCases:
    """Test edge cases."""
    
    def test_missing_data_defaults(self):
        """Strategy handles missing data gracefully."""
        lynch = PeterLynchStrategy()
        
        stock_data = {
            'ticker': 'TEST',
            'current_price': 100.00
        }
        
        result = lynch.evaluate_stock(stock_data)
        
        # Should not crash
        assert 'score' in result
        assert result['score'] >= 0
        assert 'rating' in result
    
    def test_unknown_sector(self):
        """Unknown sector gets 0 understandability points."""
        lynch = PeterLynchStrategy()
        
        stock_data = {
            'ticker': 'UNKNOWN',
            'current_price': 100.00,
            'eps': 5.00,
            'pe_ratio': 20.0,
            'earnings_growth': 0.30,
            'revenue_growth': 0.25,
            'sector': 'Quantum Computing'  # Not in familiar sectors
        }
        
        result = lynch.evaluate_stock(stock_data)
        
        # Should lose understandability points
        assert result['key_metrics']['understandability_score'] == 0
        # But still score well on other metrics
        assert result['score'] >= 60  # 35 + 30 + 15 = 80, minus understandability = 65


class TestLynchEvaluation:
    """Integration tests for complete evaluation flow."""
    
    def test_complete_evaluation_structure(self):
        """Evaluation returns all required fields."""
        lynch = PeterLynchStrategy()
        
        stock_data = {
            'ticker': 'TEST',
            'current_price': 150.00,
            'eps': 6.00,
            'pe_ratio': 25.0,
            'earnings_growth': 0.25,
            'revenue_growth': 0.20,
            'sector': 'Technology'
        }
        
        result = lynch.evaluate_stock(stock_data)
        
        # Verify all required fields
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
    
    def test_peg_ratio_in_metrics(self):
        """PEG ratio is calculated and included in metrics."""
        lynch = PeterLynchStrategy()
        
        stock_data = {
            'ticker': 'PEGTEST',
            'current_price': 100.00,
            'eps': 5.00,
            'pe_ratio': 30.0,
            'earnings_growth': 0.20,  # PEG should be 30/20 = 1.5
            'revenue_growth': 0.15,
            'sector': 'Healthcare'
        }
        
        result = lynch.evaluate_stock(stock_data)
        
        # Verify PEG is calculated correctly
        assert result['key_metrics']['peg_ratio'] == 1.5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

