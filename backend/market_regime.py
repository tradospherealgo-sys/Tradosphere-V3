"""
Market Regime Detection Module
Identifies market conditions: TRENDING, RANGING, VOLATILE, SIDEWAYS
Used for regime-aware trading decisions
"""

import numpy as np
from typing import Dict, Tuple
from logger_config import get_logger

logger = get_logger(__name__)


class MarketRegime:
    """Detect market regime based on trend strength and volatility"""

    @staticmethod
    def calculate_atr(high_prices: list, low_prices: list, close_prices: list, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(high_prices) < period:
            return 0

        tr_values = []
        for i in range(len(high_prices)):
            high_low = high_prices[i] - low_prices[i]
            high_close = abs(high_prices[i] - close_prices[i-1]) if i > 0 else 0
            low_close = abs(low_prices[i] - close_prices[i-1]) if i > 0 else 0
            tr = max(high_low, high_close, low_close)
            tr_values.append(tr)

        return np.mean(tr_values[-period:])

    @staticmethod
    def calculate_trend_strength(ema_fast: float, ema_slow: float, atr: float, current_price: float) -> float:
        """
        Calculate trend strength as percentage of ATR
        Higher = stronger trend
        """
        if atr == 0 or current_price == 0:
            return 0

        ema_diff = abs(ema_fast - ema_slow)
        trend_strength = (ema_diff / current_price) * 100  # Percentage
        return trend_strength

    @staticmethod
    def calculate_volatility(atr: float, current_price: float) -> float:
        """
        Calculate volatility as ATR percentage of price
        """
        if current_price == 0:
            return 0
        return (atr / current_price) * 100

    @staticmethod
    def detect_regime(
        candles: list,
        ema_fast: float,
        ema_slow: float,
        current_price: float,
        period: int = 14
    ) -> Dict:
        """
        Detect market regime

        Returns:
        {
            'regime': 'TRENDING' | 'RANGING' | 'VOLATILE' | 'SIDEWAYS',
            'regime_strength': 0-100 (confidence),
            'trend_direction': 'UP' | 'DOWN' | 'NEUTRAL',
            'volatility_level': 'LOW' | 'MEDIUM' | 'HIGH',
            'atr': float,
            'trend_strength_pct': float,
            'volatility_pct': float
        }
        """
        try:
            if not candles or len(candles) < period:
                return {
                    'regime': 'UNKNOWN',
                    'regime_strength': 0,
                    'trend_direction': 'NEUTRAL',
                    'volatility_level': 'UNKNOWN',
                    'atr': 0,
                    'trend_strength_pct': 0,
                    'volatility_pct': 0
                }

            # Extract OHLC data
            closes = [c['close'] for c in candles[-period:]]
            highs = [c['high'] for c in candles[-period:]]
            lows = [c['low'] for c in candles[-period:]]

            # Calculate metrics
            atr = MarketRegime.calculate_atr(highs, lows, closes, period)
            trend_strength = MarketRegime.calculate_trend_strength(ema_fast, ema_slow, atr, current_price)
            volatility = MarketRegime.calculate_volatility(atr, current_price)

            # Define thresholds (can be tuned)
            TREND_STRENGTH_THRESHOLD = 1.5  # 1.5% of price
            VOLATILITY_HIGH = 4.0  # 4% ATR
            VOLATILITY_LOW = 1.5  # 1.5% ATR

            # Determine trend direction
            if ema_fast > ema_slow:
                trend_direction = 'UP'
            elif ema_fast < ema_slow:
                trend_direction = 'DOWN'
            else:
                trend_direction = 'NEUTRAL'

            # Determine volatility level
            if volatility > VOLATILITY_HIGH:
                volatility_level = 'HIGH'
            elif volatility < VOLATILITY_LOW:
                volatility_level = 'LOW'
            else:
                volatility_level = 'MEDIUM'

            # Determine regime
            if trend_strength > TREND_STRENGTH_THRESHOLD:
                if volatility_level == 'HIGH':
                    regime = 'VOLATILE'
                    regime_strength = min(90, 50 + (trend_strength * 10))
                else:
                    regime = 'TRENDING'
                    regime_strength = min(95, 60 + (trend_strength * 15))
            elif volatility_level == 'HIGH':
                regime = 'VOLATILE'
                regime_strength = 70
            else:
                regime = 'RANGING'
                regime_strength = 60

            logger.info(
                f"📊 Market Regime: {regime} | "
                f"Direction: {trend_direction} | "
                f"Strength: {regime_strength}% | "
                f"Volatility: {volatility_level}"
            )

            return {
                'regime': regime,
                'regime_strength': int(regime_strength),
                'trend_direction': trend_direction,
                'volatility_level': volatility_level,
                'atr': round(atr, 2),
                'trend_strength_pct': round(trend_strength, 2),
                'volatility_pct': round(volatility, 2)
            }

        except Exception as e:
            logger.error(f"❌ Error detecting regime: {str(e)}")
            return {
                'regime': 'ERROR',
                'regime_strength': 0,
                'trend_direction': 'NEUTRAL',
                'volatility_level': 'UNKNOWN',
                'atr': 0,
                'trend_strength_pct': 0,
                'volatility_pct': 0
            }


def get_regime_context(regime_data: Dict) -> str:
    """
    Get human-readable regime context for signal generation
    """
    regime = regime_data['regime']
    direction = regime_data['trend_direction']
    strength = regime_data['regime_strength']
    volatility = regime_data['volatility_level']

    if regime == 'TRENDING':
        if direction == 'UP' and strength > 75:
            return "strong_uptrend_high_momentum"
        elif direction == 'UP':
            return "uptrend_moderate_momentum"
        elif direction == 'DOWN' and strength > 75:
            return "strong_downtrend_high_momentum"
        elif direction == 'DOWN':
            return "downtrend_moderate_momentum"
    elif regime == 'RANGING':
        return "range_bound_consolidation"
    elif regime == 'VOLATILE':
        if direction == 'UP':
            return "high_volatility_bullish_bias"
        elif direction == 'DOWN':
            return "high_volatility_bearish_bias"
        else:
            return "high_volatility_directionless"

    return "sideways_uncertain"
