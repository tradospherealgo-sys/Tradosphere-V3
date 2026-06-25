"""
Composite Signal Generator
Generates regime-aware trading signals with confidence scores and context-aware wording
Uses market regime, technical indicators, and options data for signal generation
"""

from typing import Dict, List
from logger_config import get_logger
from market_regime import MarketRegime, get_regime_context

logger = get_logger(__name__)


class CompositeSignalGenerator:
    """Generate trading signals based on multiple factors with confidence scoring"""

    def __init__(self):
        self.market_regime = MarketRegime()

    def score_technical_indicators(
        self,
        ema_fast: float,
        ema_slow: float,
        ema_long: float,
        rsi: float,
        bb_position: float,  # -1 to 1 (lower to upper band)
        macd_signal: str,  # 'BULLISH' or 'BEARISH'
        volume_confirm: bool
    ) -> Dict:
        """
        Score technical indicators on 0-40 scale (40% weight)

        Args:
            ema_fast: Fast EMA (20)
            ema_slow: Medium EMA (50)
            ema_long: Long EMA (200)
            rsi: RSI value (0-100)
            bb_position: Bollinger Band position (-1 to 1)
            macd_signal: MACD direction
            volume_confirm: Volume confirmation

        Returns:
        {
            'score': 0-40,
            'ema_alignment': 0-15,
            'rsi_score': 0-10,
            'bb_score': 0-10,
            'volume_score': 0-5,
            'details': str
        }
        """
        score = 0
        details = []

        # EMA Alignment (0-15 points)
        if ema_fast > ema_slow > ema_long:
            ema_score = 15
            details.append("Strong bullish EMA alignment (20>50>200)")
        elif ema_fast > ema_slow and ema_slow > ema_long * 0.98:
            ema_score = 12
            details.append("Good bullish EMA alignment")
        elif ema_fast < ema_slow < ema_long:
            ema_score = -10  # Bearish
            details.append("Strong bearish EMA alignment (20<50<200)")
        elif ema_fast < ema_slow and ema_slow < ema_long * 1.02:
            ema_score = -8  # Bearish
            details.append("Good bearish EMA alignment")
        else:
            ema_score = 5
            details.append("Mixed EMA signals")

        score += max(0, ema_score)

        # RSI Score (0-10 points)
        if 30 < rsi < 70:
            rsi_score = 8
            details.append("RSI in healthy zone (30-70)")
        elif rsi <= 30:
            rsi_score = 10
            details.append("RSI oversold - potential bounce")
        elif rsi >= 70:
            rsi_score = -5
            details.append("RSI overbought - caution advised")
        else:
            rsi_score = 5
            details.append("RSI neutral")

        score += max(0, rsi_score)

        # Bollinger Band Score (0-10 points)
        if bb_position > 0.5:
            bb_score = 10
            details.append("Price at upper Bollinger Band - strong trend")
        elif bb_position > 0:
            bb_score = 7
            details.append("Price above middle band - bullish")
        elif bb_position < -0.5:
            bb_score = -8
            details.append("Price at lower band - bearish")
        elif bb_position < 0:
            bb_score = -5
            details.append("Price below middle band")
        else:
            bb_score = 3
            details.append("Price at Bollinger Band middle")

        score += max(0, bb_score)

        # Volume Confirmation (0-5 points)
        if volume_confirm:
            volume_score = 5
            details.append("Volume confirmation present")
        else:
            volume_score = 0
            details.append("No volume confirmation")

        score += volume_score

        # MACD alignment
        if macd_signal == 'BULLISH':
            details.append("MACD bullish")
        elif macd_signal == 'BEARISH':
            details.append("MACD bearish")

        return {
            'score': max(0, score),
            'ema_alignment': max(0, ema_score),
            'rsi_score': max(0, rsi_score),
            'bb_score': max(0, bb_score),
            'volume_score': volume_score,
            'details': ' | '.join(details)
        }

    def score_market_regime(self, regime_data: Dict) -> Dict:
        """
        Score market regime on 0-30 scale (30% weight)

        Returns:
        {
            'score': 0-30,
            'regime_alignment': str,
            'details': str
        }
        """
        regime = regime_data['regime']
        strength = regime_data['regime_strength']
        direction = regime_data['trend_direction']

        score = 0
        details = []

        if regime == 'TRENDING':
            if direction == 'UP' and strength > 80:
                score = 30
                details.append("Strong uptrend with high confidence")
            elif direction == 'UP':
                score = 25
                details.append("Confirmed uptrend")
            elif direction == 'DOWN' and strength > 80:
                score = -25
                details.append("Strong downtrend - avoid longs")
            elif direction == 'DOWN':
                score = -20
                details.append("Confirmed downtrend")
        elif regime == 'RANGING':
            score = 10
            details.append("Range-bound market - mean reversion plays")
        elif regime == 'VOLATILE':
            if direction == 'UP':
                score = 15
                details.append("High volatility with bullish bias")
            else:
                score = -10
                details.append("High volatility with bearish pressure")
        else:
            score = 5
            details.append("Sideways/uncertain market")

        return {
            'score': max(0, score),
            'regime_name': regime,
            'regime_alignment': direction,
            'details': ' | '.join(details)
        }

    def score_options_context(self, options_data: Dict) -> Dict:
        """
        Score options intelligence on 0-20 scale (20% weight)

        Args:
            options_data: {
                'pcr': 'BULLISH'|'BEARISH'|'NEUTRAL',
                'max_pain_bias': 'UPSIDE'|'DOWNSIDE',
                'oi_buildup': bool,
                'call_oi_increase': bool
            }

        Returns:
        {
            'score': 0-20,
            'options_context': str,
            'details': str
        }
        """
        score = 0
        details = []

        # PCR analysis
        pcr = options_data.get('pcr', 'NEUTRAL')
        if pcr == 'BULLISH':
            score += 8
            details.append("Low Put/Call ratio - bullish positioning")
        elif pcr == 'BEARISH':
            score -= 8
            details.append("High Put/Call ratio - bearish positioning")
        else:
            score += 3
            details.append("Balanced Put/Call ratio")

        # Max Pain bias
        max_pain = options_data.get('max_pain_bias', 'NEUTRAL')
        if max_pain == 'UPSIDE':
            score += 7
            details.append("Max pain above spot - upside bias")
        elif max_pain == 'DOWNSIDE':
            score -= 7
            details.append("Max pain below spot - downside bias")

        # OI buildup
        if options_data.get('oi_buildup', False):
            score += 5
            details.append("OI buildup indicates fresh positions")

        return {
            'score': max(0, score),
            'pcr_signal': pcr,
            'max_pain_bias': max_pain,
            'details': ' | '.join(details)
        }

    def score_risk_validation(self, risk_validation: Dict) -> Dict:
        """
        Score risk validation on 0-10 scale (10% weight)

        Returns score based on whether trade passes risk checks
        """
        score = 0
        details = []

        if risk_validation.get('is_valid', False):
            score = 10
            details.append(f"Risk approved: {risk_validation.get('message', '')}")
        else:
            score = 0
            details.append(f"Risk violation: {risk_validation.get('message', '')}")

        return {
            'score': score,
            'details': ' | '.join(details)
        }

    def generate_signal(
        self,
        technical_score: Dict,
        regime_score: Dict,
        options_score: Dict,
        risk_score: Dict,
        current_price: float,
        entry_price: float,
        current_price_level: str = 'NEUTRAL'  # 'SUPPORT', 'RESISTANCE', 'BREAKOUT', 'NEUTRAL'
    ) -> Dict:
        """
        Generate composite signal with confidence scoring

        Args:
            technical_score: From score_technical_indicators()
            regime_score: From score_market_regime()
            options_score: From score_options_context()
            risk_score: From score_risk_validation()
            current_price: Current market price
            entry_price: Entry price for signal
            current_price_level: Current price level context

        Returns:
        {
            'signal': 'BUY_HIGH_CONFIDENCE' | 'BUY_MEDIUM_CONFIDENCE' | 'HOLD' | 'SELL_...' | 'NO_TRADE',
            'confidence_score': 0-100,
            'signal_wording': 'Contextual share market terminology',
            'total_score': int,
            'score_breakdown': {
                'technical': int,
                'regime': int,
                'options': int,
                'risk': int
            },
            'trade_context': str,
            'recommendation': str,
            'risk_level': 'LOW' | 'MEDIUM' | 'HIGH' | 'TOO_HIGH'
        }
        """
        # Calculate weighted total score
        tech_weight = 0.40
        regime_weight = 0.30
        opt_weight = 0.20
        risk_weight = 0.10

        total_score = (
            (technical_score['score'] * tech_weight) +
            (regime_score['score'] * regime_weight) +
            (options_score['score'] * opt_weight) +
            (risk_score['score'] * risk_weight)
        )

        # Normalize to 0-100 scale
        confidence_score = int(total_score / 0.4)  # Max possible is 40
        confidence_score = min(100, max(0, confidence_score))

        # Determine signal direction based on scores
        is_bullish = technical_score['score'] > 15 and regime_score['score'] > 0
        is_bearish = technical_score['score'] < 5 and regime_score['score'] < 0

        # Generate signal with contextual wording
        if risk_score['score'] == 0:
            signal = 'NO_TRADE'
            wording = "Trade rejected: Risk management failure"
            recommendation = f"❌ {risk_score['details']}"
            risk_level = 'TOO_HIGH'

        elif is_bullish and confidence_score >= 80:
            signal = 'BUY_HIGH_CONFIDENCE'
            wording = self._get_bullish_wording(
                technical_score, regime_score, options_score, current_price_level
            )
            recommendation = f"🟢 Strong buy signal - High conviction"
            risk_level = 'LOW'

        elif is_bullish and confidence_score >= 60:
            signal = 'BUY_MEDIUM_CONFIDENCE'
            wording = self._get_bullish_wording(
                technical_score, regime_score, options_score, current_price_level, medium=True
            )
            recommendation = f"🟡 Moderate buy - Build position carefully"
            risk_level = 'MEDIUM'

        elif is_bearish and confidence_score >= 70:
            signal = 'SELL_HIGH_CONFIDENCE'
            wording = self._get_bearish_wording(
                technical_score, regime_score, options_score, current_price_level
            )
            recommendation = f"🔴 Strong sell signal - Exit longs"
            risk_level = 'LOW'

        elif is_bearish and confidence_score >= 50:
            signal = 'SELL_MEDIUM_CONFIDENCE'
            wording = self._get_bearish_wording(
                technical_score, regime_score, options_score, current_price_level, medium=True
            )
            recommendation = f"🟠 Moderate caution - Reduce exposure"
            risk_level = 'MEDIUM'

        else:
            signal = 'HOLD'
            wording = "Market signals are mixed - No clear direction"
            recommendation = f"⚪ Hold position - Wait for clarity"
            risk_level = 'MEDIUM'

        logger.info(
            f"\n{'='*70}\n"
            f"📊 COMPOSITE SIGNAL GENERATED\n"
            f"Signal: {signal} | Confidence: {confidence_score}%\n"
            f"Wording: {wording}\n"
            f"{'='*70}"
        )

        return {
            'signal': signal,
            'confidence_score': confidence_score,
            'signal_wording': wording,
            'total_score': int(total_score),
            'score_breakdown': {
                'technical': technical_score['score'],
                'regime': regime_score['score'],
                'options': options_score['score'],
                'risk': risk_score['score']
            },
            'trade_context': regime_score['details'],
            'recommendation': recommendation,
            'risk_level': risk_level
        }

    def _get_bullish_wording(self, tech, regime, options, price_level, medium=False):
        """Generate contextual bullish signal wording"""
        base = "Strong" if not medium else "Moderate"

        if price_level == 'BREAKOUT':
            return f"{base} breakout above resistance with bullish alignment - Fresh upside momentum"
        elif price_level == 'SUPPORT':
            return f"{base} bounce from support with trend confirmation - Higher probability reversal"
        elif regime['details'] and 'uptrend' in regime['details'].lower():
            return f"{base} continuation in established uptrend - Ride the momentum"
        else:
            return f"{base} bullish technical setup with positive regime confirmation"

    def _get_bearish_wording(self, tech, regime, options, price_level, medium=False):
        """Generate contextual bearish signal wording"""
        base = "Strong" if not medium else "Moderate"

        if price_level == 'BREAKOUT':
            return f"{base} breakdown below support with bearish alignment - Fresh downside momentum"
        elif price_level == 'RESISTANCE':
            return f"{base} rejection at resistance with trend confirmation - Higher probability reversal"
        elif regime['details'] and 'downtrend' in regime['details'].lower():
            return f"{base} continuation in established downtrend - Risk remains high"
        else:
            return f"{base} bearish technical setup with negative regime confirmation"
