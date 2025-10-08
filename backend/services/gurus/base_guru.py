"""
Base Guru Strategy Abstract Class

This module defines the abstract base class for all investment guru strategies.
Each guru (Buffett, Lynch, Graham, Dalio) will inherit from this class and
implement their unique evaluation logic.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any


class BaseGuru(ABC):
    """
    Abstract base class for investment guru strategies.
    
    All guru implementations must inherit from this class and implement
    the abstract methods: evaluate_stock, get_key_metrics, and generate_insight.
    
    Attributes:
        name: The guru's name (e.g., "Warren Buffett")
        description: Brief description of the investment philosophy
        strategy_type: Type of strategy ('value', 'growth', 'balanced')
        risk_level: Risk level of the strategy ('low', 'medium', 'high')
    """
    
    def __init__(self):
        """Initialize the base guru with default attributes."""
        self.name: str = "Base Guru"
        self.description: str = "Abstract investment strategy"
        self.strategy_type: str = "balanced"  # 'value', 'growth', 'balanced'
        self.risk_level: str = "medium"  # 'low', 'medium', 'high'
    
    # =========================================================================
    # ABSTRACT METHODS - Must be implemented by subclasses
    # =========================================================================
    
    @abstractmethod
    def evaluate_stock(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a stock based on the guru's investment criteria.
        
        Args:
            stock_data: Dictionary containing stock financial data.
                Expected keys depend on the specific guru strategy but typically include:
                - ticker: str
                - current_price: float
                - eps: float (earnings per share)
                - roe: float (return on equity, as decimal 0-1)
                - pe_ratio: float
                - debt_to_equity: float
                - net_margin: float (as decimal 0-1)
                - revenue_growth: float (as decimal 0-1)
                - industry_pe: float (optional)
                
        Returns:
            Dictionary with evaluation results:
            {
                'score': int (0-100),
                'rating': str ('excellent'|'good'|'fair'|'poor'),
                'recommendation': str ('strong_buy'|'buy'|'hold'|'sell'),
                'reasoning': str,
                'key_metrics': dict,
                'fair_value': float,
                'margin_of_safety': float
            }
            
        Example:
            >>> guru = SomeGuru()
            >>> stock_data = {
            ...     'ticker': 'AAPL',
            ...     'current_price': 150.00,
            ...     'eps': 6.00,
            ...     'roe': 0.30,
            ...     'pe_ratio': 25.0
            ... }
            >>> result = guru.evaluate_stock(stock_data)
            >>> print(result['rating'])
            'excellent'
        """
        pass
    
    @abstractmethod
    def get_key_metrics(self) -> List[str]:
        """
        Get the list of key financial metrics this guru focuses on.
        
        Returns:
            List of metric names that are most important to this strategy
            
        Example:
            >>> guru = WarrenBuffett()
            >>> metrics = guru.get_key_metrics()
            >>> print(metrics)
            ['ROE', 'Net Margin', 'Debt/Equity', 'Earnings Growth', 'P/E Ratio']
        """
        pass
    
    @abstractmethod
    def generate_insight(self, stock_data: Dict[str, Any], evaluation: Dict[str, Any]) -> str:
        """
        Generate a human-readable insight explaining the evaluation.
        
        This method creates educational content that helps beginners understand
        WHY a stock received its rating according to this guru's philosophy.
        
        Args:
            stock_data: Original stock data dictionary
            evaluation: Result from evaluate_stock()
            
        Returns:
            Multi-paragraph insight text with:
            - What the guru looks for in a stock
            - How this stock measures up
            - Key strengths and weaknesses
            - Educational context about the metrics
            
        Example:
            >>> insight = guru.generate_insight(stock_data, evaluation)
            >>> print(insight[:100])
            'Warren Buffett looks for companies with strong economic moats...'
        """
        pass
    
    # =========================================================================
    # UTILITY METHODS - Implemented in base class
    # =========================================================================
    
    def calculate_margin_of_safety(self, current_price: float, fair_value: float) -> float:
        """
        Calculate the margin of safety between current price and fair value.
        
        Margin of safety is a fundamental concept in value investing, representing
        the discount at which a stock trades relative to its estimated intrinsic value.
        
        Args:
            current_price: Current market price of the stock
            fair_value: Estimated fair/intrinsic value of the stock
            
        Returns:
            Margin of safety as a decimal (e.g., 0.25 = 25% discount)
            - Positive values indicate undervaluation (good!)
            - Negative values indicate overvaluation (caution!)
            
        Example:
            >>> guru = BaseGuru()
            >>> mos = guru.calculate_margin_of_safety(80, 100)
            >>> print(f"{mos:.1%}")  # 20.0% discount
            0.2
            >>> mos = guru.calculate_margin_of_safety(120, 100)
            >>> print(f"{mos:.1%}")  # -20.0% (overvalued)
            -0.2
        """
        if fair_value == 0:
            return 0.0
        
        margin = (fair_value - current_price) / fair_value
        return round(margin, 4)
    
    def determine_rating(self, score: int) -> str:
        """
        Convert a numerical score (0-100) to a rating label.
        
        Args:
            score: Numerical score from 0 to 100
            
        Returns:
            Rating string: 'excellent', 'good', 'fair', or 'poor'
            
        Rating thresholds:
        - 80-100: excellent (strong investment opportunity)
        - 60-79:  good (solid investment)
        - 40-59:  fair (acceptable with reservations)
        - 0-39:   poor (avoid or sell)
            
        Example:
            >>> guru = BaseGuru()
            >>> guru.determine_rating(85)
            'excellent'
            >>> guru.determine_rating(55)
            'fair'
        """
        if score >= 80:
            return 'excellent'
        elif score >= 60:
            return 'good'
        elif score >= 40:
            return 'fair'
        else:
            return 'poor'
    
    def determine_recommendation(self, score: int, margin_of_safety: float) -> str:
        """
        Determine buy/hold/sell recommendation based on score and margin of safety.
        
        Args:
            score: Overall quality score (0-100)
            margin_of_safety: Price discount from fair value (as decimal)
            
        Returns:
            Recommendation: 'strong_buy', 'buy', 'hold', or 'sell'
            
        Logic:
        - strong_buy: Excellent score (80+) AND good margin of safety (15%+)
        - buy: Good score (60+) AND some margin of safety (5%+)
        - hold: Fair score (40+) OR modest overvaluation (< -10%)
        - sell: Poor score (< 40) OR significant overvaluation (-20%+)
            
        Example:
            >>> guru = BaseGuru()
            >>> guru.determine_recommendation(85, 0.20)  # 85 score, 20% discount
            'strong_buy'
            >>> guru.determine_recommendation(70, -0.15)  # 70 score, 15% overvalued
            'hold'
        """
        # Strong buy: High quality + good price
        if score >= 80 and margin_of_safety >= 0.15:
            return 'strong_buy'
        
        # Buy: Good quality + reasonable price
        if score >= 60 and margin_of_safety >= 0.05:
            return 'buy'
        
        # Sell: Poor quality or significantly overvalued
        if score < 40 or margin_of_safety < -0.20:
            return 'sell'
        
        # Hold: Everything else
        return 'hold'
    
    def format_percentage(self, value: float) -> str:
        """
        Format a decimal value as a percentage string.
        
        Args:
            value: Decimal value (e.g., 0.25 for 25%)
            
        Returns:
            Formatted percentage string with 1 decimal place
            
        Example:
            >>> guru = BaseGuru()
            >>> guru.format_percentage(0.2567)
            '25.7%'
            >>> guru.format_percentage(-0.05)
            '-5.0%'
        """
        return f"{value * 100:.1f}%"
    
    def format_currency(self, value: float) -> str:
        """
        Format a value as USD currency string.
        
        Args:
            value: Dollar amount
            
        Returns:
            Formatted currency string
            
        Example:
            >>> guru = BaseGuru()
            >>> guru.format_currency(1234.56)
            '$1,234.56'
            >>> guru.format_currency(1500000)
            '$1,500,000.00'
        """
        return f"${value:,.2f}"
    
    def clamp(self, value: float, min_value: float, max_value: float) -> float:
        """
        Clamp a value between minimum and maximum bounds.
        
        Args:
            value: Value to clamp
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            Clamped value
            
        Example:
            >>> guru = BaseGuru()
            >>> guru.clamp(15, 10, 30)
            15
            >>> guru.clamp(5, 10, 30)
            10
            >>> guru.clamp(35, 10, 30)
            30
        """
        return max(min_value, min(max_value, value))
    
    # =========================================================================
    # STRING REPRESENTATION
    # =========================================================================
    
    def __str__(self) -> str:
        """String representation of the guru."""
        return f"{self.name} ({self.strategy_type.capitalize()} Strategy)"
    
    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"<{self.__class__.__name__}: {self.name}>"
    
    def to_dict(self) -> Dict[str, str]:
        """
        Convert guru metadata to dictionary.
        
        Returns:
            Dictionary with guru information
            
        Example:
            >>> guru = SomeGuru()
            >>> info = guru.to_dict()
            >>> print(info['name'])
            'Warren Buffett'
        """
        return {
            'name': self.name,
            'description': self.description,
            'strategy_type': self.strategy_type,
            'risk_level': self.risk_level
        }

