"""
Warren Buffett Value Investing Strategy

This module implements Warren Buffett's investment philosophy focused on:
- Quality businesses with strong economic moats
- High return on equity (ROE)
- Excellent profit margins
- Conservative debt levels
- Consistent earnings growth
- Reasonable valuations

"Price is what you pay. Value is what you get." - Warren Buffett
"""

from typing import Dict, List, Any
from backend.services.gurus.base_guru import BaseGuru


class WarrenBuffettStrategy(BaseGuru):
    """
    Warren Buffett's value investing strategy implementation.
    
    This strategy evaluates stocks based on quality metrics that indicate
    a strong "economic moat" - sustainable competitive advantages that
    protect a company's profits from competitors.
    
    Key principles:
    - Economic moat (high ROE)
    - Strong profit margins
    - Low debt
    - Consistent earnings growth
    - Reasonable price relative to value
    
    Example:
        >>> buffett = WarrenBuffettStrategy()
        >>> stock_data = {
        ...     'ticker': 'AAPL',
        ...     'current_price': 150.00,
        ...     'eps': 6.00,
        ...     'roe': 0.30,  # 30% ROE
        ...     'net_margin': 0.22,  # 22% margin
        ...     'debt_to_equity': 0.4,
        ...     'earnings_growth': 0.12,  # 12% growth
        ...     'pe_ratio': 25.0,
        ...     'industry_pe': 28.0
        ... }
        >>> evaluation = buffett.evaluate_stock(stock_data)
        >>> print(f"{evaluation['rating']}: {evaluation['score']}/100")
        excellent: 90/100
    """
    
    def __init__(self):
        """Initialize Warren Buffett strategy with value investing attributes."""
        super().__init__()
        self.name = "Warren Buffett"
        self.description = "Value investing with focus on quality and economic moat"
        self.strategy_type = "value"
        self.risk_level = "low"
    
    def evaluate_stock(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a stock using Warren Buffett's value investing criteria.
        
        Scoring breakdown (100 points total):
        - Economic Moat (ROE): 30 points
        - Profit Margins: 20 points
        - Debt Management: 20 points
        - Earnings Growth: 15 points
        - Valuation (P/E): 15 points
        
        Args:
            stock_data: Dictionary with financial data:
                - ticker: str
                - current_price: float
                - eps: float (earnings per share)
                - roe: float (return on equity, as decimal)
                - net_margin: float (net profit margin, as decimal)
                - debt_to_equity: float
                - earnings_growth: float (5-year growth rate, as decimal)
                - pe_ratio: float
                - industry_pe: float (optional)
                
        Returns:
            Evaluation dictionary with score, rating, recommendation, and analysis
        """
        # Extract data with defaults
        ticker = stock_data.get('ticker', 'UNKNOWN')
        current_price = stock_data.get('current_price', 0.0)
        eps = stock_data.get('eps', 0.0)
        roe = stock_data.get('roe', 0.0)
        net_margin = stock_data.get('net_margin', 0.0)
        debt_to_equity = stock_data.get('debt_to_equity', 0.0)
        earnings_growth = stock_data.get('earnings_growth', 0.0)
        pe_ratio = stock_data.get('pe_ratio', 0.0)
        industry_pe = stock_data.get('industry_pe', pe_ratio * 1.2)  # Default to 20% above current
        
        # Initialize scoring
        score = 0
        reasoning_parts = []
        key_metrics = {}
        
        # 1. Economic Moat - ROE (30 points)
        roe_score = 0
        if roe > 0.20:  # 20%
            roe_score = 30
            reasoning_parts.append(f"🏰 Exceptional moat with {self.format_percentage(roe)} ROE")
        elif roe > 0.15:  # 15%
            roe_score = 20
            reasoning_parts.append(f"Strong ROE of {self.format_percentage(roe)}")
        elif roe > 0.10:  # 10%
            roe_score = 10
            reasoning_parts.append(f"Moderate ROE of {self.format_percentage(roe)}")
        else:
            reasoning_parts.append(f"⚠️ Weak ROE of {self.format_percentage(roe)}")
        
        score += roe_score
        key_metrics['roe'] = roe
        key_metrics['roe_score'] = roe_score
        
        # 2. Profit Margins - Net Margin (20 points)
        margin_score = 0
        if net_margin > 0.20:  # 20%
            margin_score = 20
            reasoning_parts.append(f"💰 Excellent margins of {self.format_percentage(net_margin)}")
        elif net_margin > 0.15:  # 15%
            margin_score = 15
            reasoning_parts.append(f"Strong margins of {self.format_percentage(net_margin)}")
        elif net_margin > 0.10:  # 10%
            margin_score = 10
            reasoning_parts.append(f"Decent margins of {self.format_percentage(net_margin)}")
        else:
            reasoning_parts.append(f"⚠️ Thin margins of {self.format_percentage(net_margin)}")
        
        score += margin_score
        key_metrics['net_margin'] = net_margin
        key_metrics['margin_score'] = margin_score
        
        # 3. Debt Management - Debt/Equity (20 points)
        debt_score = 0
        if debt_to_equity < 0.5:
            debt_score = 20
            reasoning_parts.append(f"✅ Conservative debt at {debt_to_equity:.2f} D/E ratio")
        elif debt_to_equity < 1.0:
            debt_score = 10
            reasoning_parts.append(f"Manageable debt at {debt_to_equity:.2f} D/E ratio")
        else:
            reasoning_parts.append(f"⚠️ High debt at {debt_to_equity:.2f} D/E ratio")
        
        score += debt_score
        key_metrics['debt_to_equity'] = debt_to_equity
        key_metrics['debt_score'] = debt_score
        
        # 4. Consistent Earnings - Growth (15 points)
        growth_score = 0
        if earnings_growth > 0.10:  # 10%
            growth_score = 15
            reasoning_parts.append(f"📈 Strong earnings growth of {self.format_percentage(earnings_growth)}")
        elif earnings_growth > 0.05:  # 5%
            growth_score = 10
            reasoning_parts.append(f"Steady earnings growth of {self.format_percentage(earnings_growth)}")
        else:
            reasoning_parts.append(f"⚠️ Weak earnings growth of {self.format_percentage(earnings_growth)}")
        
        score += growth_score
        key_metrics['earnings_growth'] = earnings_growth
        key_metrics['growth_score'] = growth_score
        
        # 5. Valuation - P/E vs Industry (15 points)
        valuation_score = 0
        if pe_ratio > 0 and pe_ratio < industry_pe:
            valuation_score = 15
            pe_discount = ((industry_pe - pe_ratio) / industry_pe)
            reasoning_parts.append(
                f"💵 Trading at P/E of {pe_ratio:.1f} vs industry {industry_pe:.1f} "
                f"({self.format_percentage(pe_discount)} discount)"
            )
        elif pe_ratio > 0 and pe_ratio < industry_pe * 1.2:
            valuation_score = 10
            reasoning_parts.append(f"Fair P/E of {pe_ratio:.1f} vs industry {industry_pe:.1f}")
        else:
            reasoning_parts.append(f"⚠️ High P/E of {pe_ratio:.1f} vs industry {industry_pe:.1f}")
        
        score += valuation_score
        key_metrics['pe_ratio'] = pe_ratio
        key_metrics['industry_pe'] = industry_pe
        key_metrics['valuation_score'] = valuation_score
        
        # Calculate fair value using simplified DCF
        fair_value = self._calculate_fair_value(eps, earnings_growth, roe)
        key_metrics['fair_value'] = fair_value
        
        # Calculate margin of safety
        margin_of_safety = self.calculate_margin_of_safety(current_price, fair_value)
        
        # Determine rating and recommendation
        rating = self.determine_rating(score)
        recommendation = self.determine_recommendation(score, margin_of_safety)
        
        # Build complete reasoning
        reasoning = f"{ticker} Analysis:\n" + "\n".join(f"• {part}" for part in reasoning_parts)
        
        return {
            'score': score,
            'rating': rating,
            'recommendation': recommendation,
            'reasoning': reasoning,
            'key_metrics': key_metrics,
            'fair_value': fair_value,
            'margin_of_safety': margin_of_safety
        }
    
    def _calculate_fair_value(self, eps: float, growth_rate: float, roe: float) -> float:
        """
        Calculate fair value using simplified DCF model.
        
        Buffett's approach simplified:
        - Fair P/E is based on growth rate and ROE quality
        - Higher ROE commands higher P/E multiples
        - Growth is rewarded but within reason
        
        Args:
            eps: Earnings per share
            growth_rate: Expected annual growth rate (as decimal)
            roe: Return on equity (as decimal)
            
        Returns:
            Estimated fair value per share
        """
        if eps <= 0:
            return 0.0
        
        # Calculate fair P/E based on growth and quality (ROE)
        # Formula: fair_pe = growth_rate * 100 * (roe / 15%)
        # This gives higher multiples to higher quality (ROE) companies
        growth_percent = growth_rate * 100
        roe_quality_factor = roe / 0.15  # Normalize to 15% ROE baseline
        
        fair_pe = growth_percent * roe_quality_factor
        
        # Clamp P/E between reasonable bounds (10 to 30)
        fair_pe = self.clamp(fair_pe, 10, 30)
        
        # Calculate fair value
        fair_value = eps * fair_pe
        
        return round(fair_value, 2)
    
    def get_key_metrics(self) -> List[str]:
        """
        Get the list of key metrics Warren Buffett focuses on.
        
        Returns:
            List of metric names most important to this strategy
        """
        return [
            'ROE',
            'Net Margin',
            'Debt/Equity',
            'Earnings Growth',
            'P/E Ratio'
        ]
    
    def generate_insight(self, stock_data: Dict[str, Any], evaluation: Dict[str, Any]) -> str:
        """
        Generate Warren Buffett-style investment insight.
        
        Args:
            stock_data: Original stock data
            evaluation: Result from evaluate_stock()
            
        Returns:
            Multi-paragraph insight in Buffett's voice
        """
        ticker = stock_data.get('ticker', 'this company')
        score = evaluation['score']
        rating = evaluation['rating']
        fair_value = evaluation['fair_value']
        current_price = stock_data.get('current_price', 0)
        margin_of_safety = evaluation['margin_of_safety']
        metrics = evaluation['key_metrics']
        
        # Header
        insight = f"**Warren Buffett's Analysis of {ticker}**\n\n"
        
        # Overall assessment based on score
        if score >= 80:
            insight += (
                "This is a **wonderful company** trading at a reasonable price. "
                "It demonstrates the characteristics I look for: a strong economic moat, "
                "excellent management that allocates capital wisely, and a business model "
                "that should compound value for decades to come.\n\n"
            )
        elif score >= 60:
            insight += (
                "This is a **solid company** with good fundamentals. While it may not be "
                "a 'wonderful' business, it shows quality characteristics and could be "
                "worth considering at the right price.\n\n"
            )
        else:
            insight += (
                "This company **doesn't meet my quality standards**. I prefer to invest in "
                "businesses with stronger competitive advantages and better financial characteristics. "
                "It's better to pass on this one and wait for a wonderful company at a fair price.\n\n"
            )
        
        # Specific strengths and weaknesses
        insight += "**What I Look For:**\n\n"
        
        # ROE analysis
        roe = metrics.get('roe', 0)
        if roe > 0.20:
            insight += (
                f"✅ **Economic Moat**: The {self.format_percentage(roe)} return on equity "
                f"indicates this business has a strong competitive advantage. Companies that "
                f"consistently earn high returns on equity are rare and valuable.\n\n"
            )
        elif roe > 0.15:
            insight += (
                f"✅ **Solid Returns**: The {self.format_percentage(roe)} ROE shows the company "
                f"generates good returns on shareholder capital.\n\n"
            )
        else:
            insight += (
                f"⚠️ **Weak Returns**: The {self.format_percentage(roe)} ROE is below what I "
                f"look for. Great businesses should earn at least 15% on equity.\n\n"
            )
        
        # Margin analysis
        margin = metrics.get('net_margin', 0)
        if margin > 0.15:
            insight += (
                f"✅ **Pricing Power**: Net margins of {self.format_percentage(margin)} suggest "
                f"the company has pricing power and operates efficiently.\n\n"
            )
        else:
            insight += (
                f"⚠️ **Margin Pressure**: Net margins of {self.format_percentage(margin)} are "
                f"lower than I prefer. Strong businesses typically have margins above 15%.\n\n"
            )
        
        # Debt analysis
        debt = metrics.get('debt_to_equity', 0)
        if debt < 0.5:
            insight += (
                f"✅ **Financial Fortress**: With a debt-to-equity ratio of {debt:.2f}, "
                f"this company has a strong balance sheet that can weather economic storms.\n\n"
            )
        elif debt < 1.0:
            insight += (
                f"✓ **Manageable Debt**: Debt-to-equity of {debt:.2f} is acceptable but "
                f"I prefer companies with even less leverage.\n\n"
            )
        else:
            insight += (
                f"⚠️ **Too Much Debt**: A debt-to-equity ratio of {debt:.2f} concerns me. "
                f"Great businesses shouldn't need lots of debt to grow.\n\n"
            )
        
        # Valuation
        insight += "**Price vs Value:**\n\n"
        if fair_value > 0:
            if margin_of_safety > 0.20:
                insight += (
                    f"💰 **Excellent Value**: Trading at {self.format_currency(current_price)} "
                    f"vs my estimated fair value of {self.format_currency(fair_value)} gives us "
                    f"a {self.format_percentage(margin_of_safety)} margin of safety. "
                    f"This is the kind of opportunity I look for.\n\n"
                )
            elif margin_of_safety > 0:
                insight += (
                    f"Fair price at {self.format_currency(current_price)} vs fair value of "
                    f"{self.format_currency(fair_value)} ({self.format_percentage(margin_of_safety)} margin). "
                    f"Reasonable but not a bargain.\n\n"
                )
            else:
                insight += (
                    f"⚠️ **Overvalued**: At {self.format_currency(current_price)}, this stock "
                    f"trades above my fair value estimate of {self.format_currency(fair_value)}. "
                    f"No margin of safety here. I'd wait for a better price.\n\n"
                )
        
        # Buffett-style conclusion
        insight += "**The Bottom Line:**\n\n"
        if score >= 80 and margin_of_safety > 0.15:
            insight += (
                "This is a **buy-and-hold forever** candidate. If you buy wonderful companies "
                "at fair prices and let them compound, you rarely need to sell. "
                "Our favorite holding period is forever."
            )
        elif score >= 60 and margin_of_safety > 0:
            insight += (
                "This could be worth considering as part of a diversified portfolio. "
                "It's not perfect, but it shows enough quality characteristics to warrant attention."
            )
        else:
            insight += (
                "**Pass on this one.** The best investments are made by being patient and "
                "waiting for wonderful companies to become available at attractive prices. "
                "This doesn't meet that standard today."
            )
        
        return insight

