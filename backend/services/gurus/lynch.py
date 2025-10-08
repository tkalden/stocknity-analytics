"""
Peter Lynch GARP (Growth at Reasonable Price) Strategy

This module implements Peter Lynch's investment philosophy focused on:
- Finding fast-growing companies at reasonable prices
- PEG ratio as the primary valuation metric
- Strong revenue and earnings growth
- Understandable businesses (avoid complex sectors)
- Looking for "10-baggers" - stocks that can increase 10x

"Go for a business that any idiot can run - because sooner or later, any idiot probably is going to run it." - Peter Lynch
"""

from typing import Dict, List, Any
from backend.services.gurus.base_guru import BaseGuru


class PeterLynchStrategy(BaseGuru):
    """
    Peter Lynch's GARP (Growth at Reasonable Price) strategy implementation.
    
    This strategy focuses on finding growing companies trading at reasonable
    valuations, as measured primarily by the PEG ratio (Price/Earnings to Growth).
    
    Key principles:
    - PEG ratio < 1 is excellent (growth at bargain price)
    - Strong revenue and earnings growth
    - Understandable business models
    - Reasonable valuations relative to growth rates
    
    Example:
        >>> lynch = PeterLynchStrategy()
        >>> stock_data = {
        ...     'ticker': 'AMZN',
        ...     'current_price': 150.00,
        ...     'eps': 3.00,
        ...     'pe_ratio': 50.0,
        ...     'earnings_growth': 0.40,  # 40% growth
        ...     'revenue_growth': 0.25,  # 25% growth
        ...     'sector': 'Technology'
        ... }
        >>> evaluation = lynch.evaluate_stock(stock_data)
        >>> print(f"{evaluation['rating']}: {evaluation['score']}/100")
        excellent: 85/100
    """
    
    # Familiar sectors that Lynch preferred (understandable businesses)
    FAMILIAR_SECTORS = [
        'Technology',
        'Consumer Cyclical',
        'Consumer Defensive',
        'Healthcare',
        'Retail',
        'Industrials',
        'Communication Services'
    ]
    
    def __init__(self):
        """Initialize Peter Lynch strategy with growth investing attributes."""
        super().__init__()
        self.name = "Peter Lynch"
        self.description = "Growth at reasonable price - find growing companies with good valuations"
        self.strategy_type = "growth"
        self.risk_level = "medium"
    
    def evaluate_stock(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a stock using Peter Lynch's GARP criteria.
        
        Scoring breakdown (100 points total):
        - PEG Ratio: 35 points (primary metric)
        - Revenue Growth: 30 points
        - Earnings Growth: 20 points
        - Understandability: 15 points
        
        Args:
            stock_data: Dictionary with financial data:
                - ticker: str
                - current_price: float
                - eps: float (earnings per share)
                - pe_ratio: float
                - earnings_growth: float (as decimal, e.g., 0.25 = 25%)
                - revenue_growth: float (as decimal)
                - sector: str (optional)
                
        Returns:
            Evaluation dictionary with score, rating, recommendation, and analysis
        """
        # Extract data with defaults
        ticker = stock_data.get('ticker', 'UNKNOWN')
        current_price = stock_data.get('current_price', 0.0)
        eps = stock_data.get('eps', 0.0)
        pe_ratio = stock_data.get('pe_ratio', 0.0)
        earnings_growth = stock_data.get('earnings_growth', 0.0)
        revenue_growth = stock_data.get('revenue_growth', 0.0)
        sector = stock_data.get('sector', 'Unknown')
        
        # Calculate PEG ratio
        peg_ratio = self._calculate_peg_ratio(pe_ratio, earnings_growth)
        
        # Initialize scoring
        score = 0
        reasoning_parts = []
        key_metrics = {}
        
        # 1. PEG Ratio (35 points) - PRIMARY METRIC
        peg_score = 0
        if peg_ratio > 0:
            if peg_ratio < 1.0:
                peg_score = 35
                reasoning_parts.append(
                    f"🎯 Excellent PEG ratio of {peg_ratio:.2f} - growth at bargain price!"
                )
            elif peg_ratio < 1.5:
                peg_score = 25
                reasoning_parts.append(
                    f"✅ Good PEG ratio of {peg_ratio:.2f} - fair price for growth"
                )
            elif peg_ratio < 2.0:
                peg_score = 15
                reasoning_parts.append(
                    f"Fair PEG ratio of {peg_ratio:.2f} - acceptable but not a bargain"
                )
            else:
                reasoning_parts.append(
                    f"⚠️ High PEG ratio of {peg_ratio:.2f} - paying too much for growth"
                )
        else:
            reasoning_parts.append("⚠️ Unable to calculate PEG ratio (negative or zero growth)")
        
        score += peg_score
        key_metrics['peg_ratio'] = peg_ratio
        key_metrics['peg_score'] = peg_score
        
        # 2. Revenue Growth (30 points)
        revenue_score = 0
        if revenue_growth > 0.20:  # 20%
            revenue_score = 30
            reasoning_parts.append(
                f"🚀 Strong revenue momentum at {self.format_percentage(revenue_growth)} growth"
            )
        elif revenue_growth > 0.15:  # 15%
            revenue_score = 20
            reasoning_parts.append(
                f"Good revenue growth of {self.format_percentage(revenue_growth)}"
            )
        elif revenue_growth > 0.10:  # 10%
            revenue_score = 10
            reasoning_parts.append(
                f"Moderate revenue growth of {self.format_percentage(revenue_growth)}"
            )
        else:
            reasoning_parts.append(
                f"⚠️ Weak revenue growth of {self.format_percentage(revenue_growth)}"
            )
        
        score += revenue_score
        key_metrics['revenue_growth'] = revenue_growth
        key_metrics['revenue_score'] = revenue_score
        
        # 3. Earnings Growth (20 points)
        eps_growth_score = 0
        if earnings_growth > 0.25:  # 25%
            eps_growth_score = 20
            reasoning_parts.append(
                f"💰 Excellent earnings growth of {self.format_percentage(earnings_growth)}"
            )
        elif earnings_growth > 0.15:  # 15%
            eps_growth_score = 15
            reasoning_parts.append(
                f"Strong earnings growth of {self.format_percentage(earnings_growth)}"
            )
        elif earnings_growth > 0.10:  # 10%
            eps_growth_score = 10
            reasoning_parts.append(
                f"Decent earnings growth of {self.format_percentage(earnings_growth)}"
            )
        else:
            reasoning_parts.append(
                f"⚠️ Slow earnings growth of {self.format_percentage(earnings_growth)}"
            )
        
        score += eps_growth_score
        key_metrics['earnings_growth'] = earnings_growth
        key_metrics['eps_growth_score'] = eps_growth_score
        
        # 4. Understandability - Familiar Sector (15 points)
        understandability_score = 0
        if sector in self.FAMILIAR_SECTORS:
            understandability_score = 15
            reasoning_parts.append(
                f"📚 Understandable business in {sector} sector"
            )
        else:
            reasoning_parts.append(
                f"⚠️ Complex or unfamiliar sector: {sector}"
            )
        
        score += understandability_score
        key_metrics['sector'] = sector
        key_metrics['understandability_score'] = understandability_score
        
        # Calculate fair value based on PEG ratio
        fair_value = self._calculate_fair_value(eps, earnings_growth)
        key_metrics['fair_value'] = fair_value
        key_metrics['pe_ratio'] = pe_ratio
        
        # Calculate margin of safety
        margin_of_safety = self.calculate_margin_of_safety(current_price, fair_value)
        
        # Determine rating and recommendation
        rating = self.determine_rating(score)
        recommendation = self.determine_recommendation(score, margin_of_safety)
        
        # Build complete reasoning
        reasoning = f"{ticker} GARP Analysis:\n" + "\n".join(f"• {part}" for part in reasoning_parts)
        
        return {
            'score': score,
            'rating': rating,
            'recommendation': recommendation,
            'reasoning': reasoning,
            'key_metrics': key_metrics,
            'fair_value': fair_value,
            'margin_of_safety': margin_of_safety
        }
    
    def _calculate_peg_ratio(self, pe_ratio: float, earnings_growth: float) -> float:
        """
        Calculate PEG (Price/Earnings to Growth) ratio.
        
        PEG = P/E ratio / (earnings growth rate * 100)
        
        A PEG ratio:
        - < 1.0: Undervalued relative to growth (excellent)
        - = 1.0: Fairly valued
        - > 1.0: Overvalued relative to growth
        
        Args:
            pe_ratio: Price to earnings ratio
            earnings_growth: Earnings growth rate as decimal (e.g., 0.25 = 25%)
            
        Returns:
            PEG ratio, or 0 if calculation is invalid
        """
        if earnings_growth <= 0 or pe_ratio <= 0:
            return 0.0
        
        # Convert growth rate to percentage
        growth_percent = earnings_growth * 100
        
        peg = pe_ratio / growth_percent
        return round(peg, 2)
    
    def _calculate_fair_value(self, eps: float, earnings_growth: float) -> float:
        """
        Calculate fair value using Lynch's PEG approach.
        
        Lynch believed a fair PEG ratio is around 1.5, meaning you should
        pay roughly 1.5x the growth rate in P/E ratio.
        
        Args:
            eps: Earnings per share
            earnings_growth: Expected annual growth rate (as decimal)
            
        Returns:
            Estimated fair value per share
        """
        if eps <= 0 or earnings_growth <= 0:
            return 0.0
        
        # Lynch's target PEG ratio
        fair_peg = 1.5
        
        # Convert growth to percentage
        growth_percent = earnings_growth * 100
        
        # Calculate fair P/E based on growth
        # fair_pe = fair_peg * growth_rate
        fair_pe = fair_peg * growth_percent
        
        # Clamp P/E to reasonable bounds (10 to 50 for growth stocks)
        fair_pe = self.clamp(fair_pe, 10, 50)
        
        # Calculate fair value
        fair_value = eps * fair_pe
        
        return round(fair_value, 2)
    
    def get_key_metrics(self) -> List[str]:
        """
        Get the list of key metrics Peter Lynch focuses on.
        
        Returns:
            List of metric names most important to this strategy
        """
        return [
            'PEG Ratio',
            'Revenue Growth',
            'EPS Growth',
            'P/E Ratio',
            'Sector'
        ]
    
    def generate_insight(self, stock_data: Dict[str, Any], evaluation: Dict[str, Any]) -> str:
        """
        Generate Peter Lynch-style investment insight.
        
        Args:
            stock_data: Original stock data
            evaluation: Result from evaluate_stock()
            
        Returns:
            Multi-paragraph insight in Lynch's voice
        """
        ticker = stock_data.get('ticker', 'this company')
        score = evaluation['score']
        rating = evaluation['rating']
        fair_value = evaluation['fair_value']
        current_price = stock_data.get('current_price', 0)
        margin_of_safety = evaluation['margin_of_safety']
        metrics = evaluation['key_metrics']
        
        # Header
        insight = f"**Peter Lynch's Analysis of {ticker}**\n\n"
        
        # Overall assessment based on score
        if score >= 80:
            insight += (
                "This looks like a **potential 10-bagger!** 🚀 It's a fast-growing company "
                "trading at a reasonable price. These are the kinds of stocks that can multiply "
                "your investment many times over if you hold them long enough.\n\n"
            )
        elif score >= 60:
            insight += (
                "This is a **solid growth story** with acceptable valuations. While it may not "
                "be the next Amazon, it shows the characteristics of a company that can deliver "
                "good returns if the growth continues.\n\n"
            )
        else:
            insight += (
                "The growth here **isn't worth the price**. I'd rather find a company growing "
                "faster for the same price, or pay less for this level of growth. There are "
                "better opportunities out there.\n\n"
            )
        
        # PEG Ratio analysis (PRIMARY METRIC)
        insight += "**The PEG Ratio - My Favorite Number:**\n\n"
        peg = metrics.get('peg_ratio', 0)
        earnings_growth = metrics.get('earnings_growth', 0)
        pe_ratio = metrics.get('pe_ratio', 0)
        
        if peg > 0:
            if peg < 1.0:
                insight += (
                    f"🎯 **PEG Ratio: {peg:.2f}** - This is excellent! With a P/E of {pe_ratio:.1f} "
                    f"and earnings growing at {self.format_percentage(earnings_growth)}, you're "
                    f"getting growth at a bargain price. A PEG under 1.0 means the stock is "
                    f"undervalued relative to its growth rate.\n\n"
                )
            elif peg < 1.5:
                insight += (
                    f"✅ **PEG Ratio: {peg:.2f}** - Fair price for the growth. The P/E of {pe_ratio:.1f} "
                    f"is reasonable given {self.format_percentage(earnings_growth)} earnings growth. "
                    f"Not a screaming bargain, but not overpriced either.\n\n"
                )
            elif peg < 2.0:
                insight += (
                    f"**PEG Ratio: {peg:.2f}** - You're paying a premium for growth here. With a "
                    f"P/E of {pe_ratio:.1f} and {self.format_percentage(earnings_growth)} growth, "
                    f"this isn't terrible, but I'd prefer to see the PEG closer to 1.0.\n\n"
                )
            else:
                insight += (
                    f"⚠️ **PEG Ratio: {peg:.2f}** - Too expensive! A P/E of {pe_ratio:.1f} for "
                    f"{self.format_percentage(earnings_growth)} growth means you're overpaying. "
                    f"I'd wait for a better entry point or look elsewhere.\n\n"
                )
        else:
            insight += (
                "⚠️ **PEG Ratio: Cannot calculate** - Without positive earnings growth, "
                "it's hard to justify a growth stock valuation. This is a red flag.\n\n"
            )
        
        # Growth momentum
        insight += "**The Growth Story:**\n\n"
        revenue_growth = metrics.get('revenue_growth', 0)
        
        if revenue_growth > 0.20 and earnings_growth > 0.20:
            insight += (
                f"💪 **Strong momentum** with {self.format_percentage(revenue_growth)} revenue growth "
                f"and {self.format_percentage(earnings_growth)} earnings growth. When both revenue "
                f"and earnings are growing fast, that's a sign the business model is working.\n\n"
            )
        elif revenue_growth > 0.15 or earnings_growth > 0.15:
            insight += (
                f"Decent growth with revenue at {self.format_percentage(revenue_growth)} and "
                f"earnings at {self.format_percentage(earnings_growth)}. Not spectacular, but "
                f"consistent growth is what we want to see.\n\n"
            )
        else:
            insight += (
                f"⚠️ **Slow growth** - Revenue growing at {self.format_percentage(revenue_growth)} "
                f"and earnings at {self.format_percentage(earnings_growth)}. For a growth stock, "
                f"I'd want to see higher numbers.\n\n"
            )
        
        # Understandability
        sector = metrics.get('sector', 'Unknown')
        if sector in self.FAMILIAR_SECTORS:
            insight += (
                f"✅ **I understand this business.** It's in {sector}, a sector I'm familiar with. "
                f"Never invest in something you don't understand - you can't predict what you "
                f"don't comprehend.\n\n"
            )
        else:
            insight += (
                f"⚠️ **Complex sector:** {sector}. I prefer to invest in businesses I understand. "
                f"If you can't explain what a company does in two minutes, you probably shouldn't "
                f"own it.\n\n"
            )
        
        # Valuation
        insight += "**What Should You Pay?**\n\n"
        if fair_value > 0:
            if margin_of_safety > 0.20:
                insight += (
                    f"💰 **Great value!** At {self.format_currency(current_price)}, you're buying "
                    f"below my fair value estimate of {self.format_currency(fair_value)} "
                    f"({self.format_percentage(margin_of_safety)} discount). This gives you a "
                    f"margin of safety if growth slows.\n\n"
                )
            elif margin_of_safety > 0:
                insight += (
                    f"Fair price at {self.format_currency(current_price)} vs my fair value of "
                    f"{self.format_currency(fair_value)}. You're getting a modest "
                    f"{self.format_percentage(margin_of_safety)} discount.\n\n"
                )
            else:
                insight += (
                    f"⚠️ **Pricey!** At {self.format_currency(current_price)}, you're paying above "
                    f"my fair value of {self.format_currency(fair_value)}. I'd wait for a pullback "
                    f"before buying.\n\n"
                )
        
        # Lynch-style conclusion
        insight += "**My Recommendation:**\n\n"
        if score >= 80 and margin_of_safety > 0.10:
            insight += (
                "**Strong Buy.** This has the makings of a big winner - fast growth, reasonable "
                "valuation, and an understandable business. These don't come along every day. "
                "Consider starting a position and adding more if the growth story continues."
            )
        elif score >= 60:
            insight += (
                "**Worth watching.** The growth is good but the price might be a bit rich. "
                "Put it on your watchlist and wait for a better entry point, or start with "
                "a small position and add more on dips."
            )
        else:
            insight += (
                "**Pass for now.** Either the growth isn't strong enough or the valuation is "
                "too high. There are better opportunities in the market. Remember: you don't "
                "have to swing at every pitch - wait for the fat ones right over the plate."
            )
        
        return insight

