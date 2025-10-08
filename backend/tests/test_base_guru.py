"""
Tests for Base Guru Abstract Class

This module tests the BaseGuru abstract class and its utility methods.
"""

import pytest
from backend.services.gurus.base_guru import BaseGuru
from typing import Dict, List, Any


# Create a concrete implementation for testing
class TestGuru(BaseGuru):
    """Concrete test implementation of BaseGuru."""
    
    def __init__(self):
        super().__init__()
        self.name = "Test Guru"
        self.description = "Test strategy for unit tests"
        self.strategy_type = "value"
        self.risk_level = "low"
    
    def evaluate_stock(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simple test evaluation."""
        return {
            'score': 75,
            'rating': self.determine_rating(75),
            'recommendation': 'buy',
            'reasoning': 'Test reasoning',
            'key_metrics': {'test_metric': 100},
            'fair_value': 100.0,
            'margin_of_safety': 0.20
        }
    
    def get_key_metrics(self) -> List[str]:
        """Return test metrics."""
        return ['Test Metric 1', 'Test Metric 2']
    
    def generate_insight(self, stock_data: Dict[str, Any], evaluation: Dict[str, Any]) -> str:
        """Generate test insight."""
        return "This is a test insight explaining the evaluation."


class TestBaseGuruInstantiation:
    """Test BaseGuru instantiation and abstract methods."""
    
    def test_cannot_instantiate_base_guru_directly(self):
        """BaseGuru is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseGuru()
    
    def test_can_instantiate_concrete_guru(self):
        """Concrete implementation can be instantiated."""
        guru = TestGuru()
        assert guru.name == "Test Guru"
        assert guru.strategy_type == "value"
        assert guru.risk_level == "low"


class TestMarginOfSafety:
    """Test margin of safety calculation."""
    
    def test_margin_of_safety_undervalued(self):
        """Stock trading below fair value has positive margin."""
        guru = TestGuru()
        mos = guru.calculate_margin_of_safety(current_price=80, fair_value=100)
        assert mos == 0.20  # 20% discount
    
    def test_margin_of_safety_overvalued(self):
        """Stock trading above fair value has negative margin."""
        guru = TestGuru()
        mos = guru.calculate_margin_of_safety(current_price=120, fair_value=100)
        assert mos == -0.20  # 20% premium
    
    def test_margin_of_safety_fair_value(self):
        """Stock at fair value has zero margin."""
        guru = TestGuru()
        mos = guru.calculate_margin_of_safety(current_price=100, fair_value=100)
        assert mos == 0.0
    
    def test_margin_of_safety_zero_fair_value(self):
        """Handle edge case of zero fair value."""
        guru = TestGuru()
        mos = guru.calculate_margin_of_safety(current_price=50, fair_value=0)
        assert mos == 0.0


class TestRatingDetermination:
    """Test score to rating conversion."""
    
    def test_excellent_rating(self):
        """Score 80+ gives excellent rating."""
        guru = TestGuru()
        assert guru.determine_rating(100) == 'excellent'
        assert guru.determine_rating(85) == 'excellent'
        assert guru.determine_rating(80) == 'excellent'
    
    def test_good_rating(self):
        """Score 60-79 gives good rating."""
        guru = TestGuru()
        assert guru.determine_rating(79) == 'good'
        assert guru.determine_rating(70) == 'good'
        assert guru.determine_rating(60) == 'good'
    
    def test_fair_rating(self):
        """Score 40-59 gives fair rating."""
        guru = TestGuru()
        assert guru.determine_rating(59) == 'fair'
        assert guru.determine_rating(50) == 'fair'
        assert guru.determine_rating(40) == 'fair'
    
    def test_poor_rating(self):
        """Score below 40 gives poor rating."""
        guru = TestGuru()
        assert guru.determine_rating(39) == 'poor'
        assert guru.determine_rating(20) == 'poor'
        assert guru.determine_rating(0) == 'poor'


class TestRecommendationDetermination:
    """Test buy/hold/sell recommendation logic."""
    
    def test_strong_buy_recommendation(self):
        """High score + good margin = strong buy."""
        guru = TestGuru()
        rec = guru.determine_recommendation(score=85, margin_of_safety=0.20)
        assert rec == 'strong_buy'
    
    def test_buy_recommendation(self):
        """Good score + modest margin = buy."""
        guru = TestGuru()
        rec = guru.determine_recommendation(score=70, margin_of_safety=0.10)
        assert rec == 'buy'
    
    def test_hold_recommendation_fair_score(self):
        """Fair score = hold."""
        guru = TestGuru()
        rec = guru.determine_recommendation(score=55, margin_of_safety=0.05)
        assert rec == 'hold'
    
    def test_hold_recommendation_modest_overvaluation(self):
        """Modest overvaluation = hold."""
        guru = TestGuru()
        rec = guru.determine_recommendation(score=70, margin_of_safety=-0.10)
        assert rec == 'hold'
    
    def test_sell_recommendation_poor_score(self):
        """Poor score = sell."""
        guru = TestGuru()
        rec = guru.determine_recommendation(score=30, margin_of_safety=0.10)
        assert rec == 'sell'
    
    def test_sell_recommendation_overvalued(self):
        """Significantly overvalued = sell."""
        guru = TestGuru()
        rec = guru.determine_recommendation(score=70, margin_of_safety=-0.25)
        assert rec == 'sell'


class TestUtilityMethods:
    """Test utility formatting methods."""
    
    def test_format_percentage_positive(self):
        """Format positive percentage."""
        guru = TestGuru()
        assert guru.format_percentage(0.2567) == '25.7%'
        assert guru.format_percentage(0.05) == '5.0%'
    
    def test_format_percentage_negative(self):
        """Format negative percentage."""
        guru = TestGuru()
        assert guru.format_percentage(-0.15) == '-15.0%'
    
    def test_format_percentage_zero(self):
        """Format zero percentage."""
        guru = TestGuru()
        assert guru.format_percentage(0.0) == '0.0%'
    
    def test_format_currency(self):
        """Format currency values."""
        guru = TestGuru()
        assert guru.format_currency(1234.56) == '$1,234.56'
        assert guru.format_currency(1500000) == '$1,500,000.00'
        assert guru.format_currency(99.99) == '$99.99'
    
    def test_clamp_within_bounds(self):
        """Value within bounds stays unchanged."""
        guru = TestGuru()
        assert guru.clamp(15, 10, 30) == 15
    
    def test_clamp_below_minimum(self):
        """Value below min gets clamped to min."""
        guru = TestGuru()
        assert guru.clamp(5, 10, 30) == 10
    
    def test_clamp_above_maximum(self):
        """Value above max gets clamped to max."""
        guru = TestGuru()
        assert guru.clamp(35, 10, 30) == 30


class TestGuruMetadata:
    """Test guru metadata and string representations."""
    
    def test_to_dict(self):
        """Convert guru to dictionary."""
        guru = TestGuru()
        info = guru.to_dict()
        
        assert info['name'] == 'Test Guru'
        assert info['description'] == 'Test strategy for unit tests'
        assert info['strategy_type'] == 'value'
        assert info['risk_level'] == 'low'
    
    def test_str_representation(self):
        """Test __str__ method."""
        guru = TestGuru()
        assert str(guru) == "Test Guru (Value Strategy)"
    
    def test_repr_representation(self):
        """Test __repr__ method."""
        guru = TestGuru()
        assert repr(guru) == "<TestGuru: Test Guru>"


class TestAbstractMethods:
    """Test that concrete implementations provide required methods."""
    
    def test_evaluate_stock_implemented(self):
        """Concrete guru implements evaluate_stock."""
        guru = TestGuru()
        result = guru.evaluate_stock({'ticker': 'TEST'})
        
        # Verify required keys in result
        assert 'score' in result
        assert 'rating' in result
        assert 'recommendation' in result
        assert 'reasoning' in result
        assert 'key_metrics' in result
        assert 'fair_value' in result
        assert 'margin_of_safety' in result
    
    def test_get_key_metrics_implemented(self):
        """Concrete guru implements get_key_metrics."""
        guru = TestGuru()
        metrics = guru.get_key_metrics()
        
        assert isinstance(metrics, list)
        assert len(metrics) > 0
        assert all(isinstance(m, str) for m in metrics)
    
    def test_generate_insight_implemented(self):
        """Concrete guru implements generate_insight."""
        guru = TestGuru()
        stock_data = {'ticker': 'TEST'}
        evaluation = guru.evaluate_stock(stock_data)
        
        insight = guru.generate_insight(stock_data, evaluation)
        
        assert isinstance(insight, str)
        assert len(insight) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

