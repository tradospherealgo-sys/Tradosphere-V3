"""
Signals Engine - Generate actionable trade signals
Analyzes technical indicators, options data, and market conditions
"""
import logging
logger = logging.getLogger(__name__)


from typing import Dict, List, Optional
from datetime import datetime

class SignalsEngine:
    """
    Generate trading signals based on comprehensive analysis
    Combines technical indicators, options data, and market structure
    """

    @staticmethod
    def generate_signals(market_data: Dict, options_data: Dict, technical_data: Dict, symbol: str = 'NIFTY') -> List[Dict]:
        """
        Generate trade signals from comprehensive market analysis

        Args:
            market_data: Live market prices and OHLC
            options_data: Options chain with PCR and Max Pain
            technical_data: Technical indicators
            symbol: Trading symbol (NIFTY/BANKNIFTY/FINNIFTY)

        Returns:
            List of trade signals with details
        """
        signals = []

        try:
            # Extract data
            current_price = market_data.get('current_price', 0)
            price_change = market_data.get('change_percent', 0)

            rsi = technical_data.get('indicators', {}).get('rsi', 50)
            ema9 = technical_data.get('indicators', {}).get('ema_9', 0)
            ema50 = technical_data.get('indicators', {}).get('ema_50', 0)
            macd_hist = technical_data.get('macd', {}).get('histogram', 0)
            bb_upper = technical_data.get('bollinger_bands', {}).get('upper_band', 0)
            bb_lower = technical_data.get('bollinger_bands', {}).get('lower_band', 0)
            vwap = technical_data.get('indicators', {}).get('vwap', 0)
            trend = technical_data.get('trend', 'NEUTRAL')
            momentum = technical_data.get('momentum', 'NEUTRAL')

            pcr = options_data.get('pcr', 1.0)
            max_pain = options_data.get('max_pain', current_price)

            # Define strike ranges (rough estimates based on current price)
            if symbol == 'NIFTY':
                strike_interval = 100
                otm_range = 3  # 3 strikes OTM
            elif symbol == 'BANKNIFTY':
                strike_interval = 500
                otm_range = 2
            else:  # FINNIFTY
                strike_interval = 100
                otm_range = 2

            # Calculate potential strikes
            atm_call_strike = round(current_price / strike_interval) * strike_interval
            atm_put_strike = atm_call_strike

            # SIGNAL 1: Check for strong bullish setup
            bullish_score = SignalsEngine._calculate_bullish_score(
                rsi, ema9, ema50, macd_hist, current_price, vwap, trend, pcr
            )

            if bullish_score >= 75:  # Strong bullish
                call_strike = atm_call_strike + (strike_interval * otm_range)
                entry_price = current_price * 1.005  # 0.5% above current
                target = entry_price * (1 + (bullish_score / 100) * 0.03)  # 3% max return
                sl = entry_price * 0.98  # 2% stop loss

                signals.append({
                    "type": "CALL",
                    "direction": "BUY",
                    "symbol": symbol,
                    "strike": int(call_strike),
                    "entry": round(entry_price, 2),
                    "target": round(target, 2),
                    "stop_loss": round(sl, 2),
                    "confidence": min(bullish_score, 95),
                    "reasoning": f"Strong bullish setup: RSI {rsi:.1f}, EMA 9 > EMA 50, MACD positive, Price > VWAP",
                    "time_generated": datetime.now().isoformat(),
                    "risk_reward": round((target - entry_price) / (entry_price - sl), 2) if entry_price > sl else 0
                })

            elif bullish_score >= 60:  # Moderate bullish
                call_strike = atm_call_strike + (strike_interval * (otm_range - 1))
                entry_price = current_price * 1.003
                target = entry_price * (1 + (bullish_score / 100) * 0.025)
                sl = entry_price * 0.985

                signals.append({
                    "type": "CALL",
                    "direction": "BUY",
                    "symbol": symbol,
                    "strike": int(call_strike),
                    "entry": round(entry_price, 2),
                    "target": round(target, 2),
                    "stop_loss": round(sl, 2),
                    "confidence": min(bullish_score, 85),
                    "reasoning": f"Moderate bullish bias: Trend {trend}, RSI {rsi:.1f}, PCR {pcr:.2f}",
                    "time_generated": datetime.now().isoformat(),
                    "risk_reward": round((target - entry_price) / (entry_price - sl), 2) if entry_price > sl else 0
                })

            # SIGNAL 2: Check for strong bearish setup
            bearish_score = SignalsEngine._calculate_bearish_score(
                rsi, ema9, ema50, macd_hist, current_price, vwap, trend, pcr
            )

            if bearish_score >= 75:  # Strong bearish
                put_strike = atm_put_strike - (strike_interval * otm_range)
                entry_price = current_price * 0.995  # 0.5% below current
                target = entry_price * (1 - (bearish_score / 100) * 0.03)
                sl = entry_price * 1.02

                signals.append({
                    "type": "PUT",
                    "direction": "BUY",
                    "symbol": symbol,
                    "strike": int(put_strike),
                    "entry": round(entry_price, 2),
                    "target": round(target, 2),
                    "stop_loss": round(sl, 2),
                    "confidence": min(bearish_score, 95),
                    "reasoning": f"Strong bearish setup: RSI {rsi:.1f}, EMA 9 < EMA 50, MACD negative, Price < VWAP",
                    "time_generated": datetime.now().isoformat(),
                    "risk_reward": round((entry_price - target) / (sl - entry_price), 2) if sl > entry_price else 0
                })

            elif bearish_score >= 60:  # Moderate bearish
                put_strike = atm_put_strike - (strike_interval * (otm_range - 1))
                entry_price = current_price * 0.997
                target = entry_price * (1 - (bearish_score / 100) * 0.025)
                sl = entry_price * 1.015

                signals.append({
                    "type": "PUT",
                    "direction": "BUY",
                    "symbol": symbol,
                    "strike": int(put_strike),
                    "entry": round(entry_price, 2),
                    "target": round(target, 2),
                    "stop_loss": round(sl, 2),
                    "confidence": min(bearish_score, 85),
                    "reasoning": f"Moderate bearish bias: Trend {trend}, RSI {rsi:.1f}, PCR {pcr:.2f}",
                    "time_generated": datetime.now().isoformat(),
                    "risk_reward": round((entry_price - target) / (sl - entry_price), 2) if sl > entry_price else 0
                })

            # SIGNAL 3: Check for breakout/reversal at max pain
            distance_to_max_pain = abs(current_price - max_pain) / current_price * 100

            if distance_to_max_pain < 2 and trend == 'BULLISH':  # Price near max pain + bullish trend
                call_strike = atm_call_strike + (strike_interval * otm_range)
                entry_price = max_pain
                target = max_pain * 1.02
                sl = max_pain * 0.99

                signals.append({
                    "type": "CALL",
                    "direction": "BUY",
                    "symbol": symbol,
                    "strike": int(call_strike),
                    "entry": round(entry_price, 2),
                    "target": round(target, 2),
                    "stop_loss": round(sl, 2),
                    "confidence": 70,
                    "reasoning": f"Price near Max Pain ({max_pain:.0f}) with bullish trend. Potential breakout setup.",
                    "time_generated": datetime.now().isoformat(),
                    "risk_reward": round((target - entry_price) / (entry_price - sl), 2) if entry_price > sl else 0
                })

            # SIGNAL 4: High PCR reversal signal
            if pcr > 1.5 and trend == 'BULLISH':  # High put OI + bullish trend = potential reversal
                call_strike = atm_call_strike + strike_interval
                entry_price = current_price
                target = current_price * 1.01
                sl = current_price * 0.995

                signals.append({
                    "type": "CALL",
                    "direction": "BUY",
                    "symbol": symbol,
                    "strike": int(call_strike),
                    "entry": round(entry_price, 2),
                    "target": round(target, 2),
                    "stop_loss": round(sl, 2),
                    "confidence": 65,
                    "reasoning": f"High Put Call Ratio ({pcr:.2f}) suggests strong put buildup. Bullish reversal likely.",
                    "time_generated": datetime.now().isoformat(),
                    "risk_reward": round((target - entry_price) / (entry_price - sl), 2) if entry_price > sl else 0
                })

            elif pcr < 0.7 and trend == 'BEARISH':  # Low put OI + bearish trend
                put_strike = atm_put_strike - strike_interval
                entry_price = current_price
                target = current_price * 0.99
                sl = current_price * 1.005

                signals.append({
                    "type": "PUT",
                    "direction": "BUY",
                    "symbol": symbol,
                    "strike": int(put_strike),
                    "entry": round(entry_price, 2),
                    "target": round(target, 2),
                    "stop_loss": round(sl, 2),
                    "confidence": 65,
                    "reasoning": f"Low Put Call Ratio ({pcr:.2f}) suggests strong call buildup. Bearish reversal likely.",
                    "time_generated": datetime.now().isoformat(),
                    "risk_reward": round((entry_price - target) / (sl - entry_price), 2) if sl > entry_price else 0
                })

            # Sort signals by confidence (highest first)
            signals = sorted(signals, key=lambda x: x['confidence'], reverse=True)

            # Limit to top 3 signals
            return signals[:3]

        except Exception as e:
            logger.error(f"Error generating signals: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def _calculate_bullish_score(rsi: float, ema9: float, ema50: float, macd_hist: float,
                                 current_price: float, vwap: float, trend: str, pcr: float) -> float:
        """Calculate bullish bias score (0-100)"""
        score = 0

        # RSI component (0-20 points)
        if rsi < 30:
            score += 20  # Oversold, likely to bounce
        elif rsi < 50:
            score += 10  # Getting momentum
        elif rsi < 70:
            score += 5   # Still okay
        # Over 70 is overbought, no points

        # EMA component (0-25 points)
        if ema9 > ema50:
            score += 25  # Strong bullish structure
        elif ema9 > ema50 * 0.99:
            score += 15  # Close to golden cross
        else:
            score -= 10  # Bearish structure

        # MACD component (0-20 points)
        if macd_hist > 0:
            score += 20  # Positive momentum
        elif macd_hist > -10:
            score += 5   # Just started turning negative
        # Else negative momentum

        # Price vs VWAP (0-15 points)
        if current_price > vwap:
            score += 15  # Above VWAP = institutional buying
        elif current_price > vwap * 0.99:
            score += 5   # Close to VWAP
        # Below VWAP is bearish

        # Trend component (0-15 points)
        if trend == 'BULLISH':
            score += 15  # Clear uptrend
        elif 'BULLISH' in trend:
            score += 10
        # Bearish or neutral gets 0

        # PCR component (0-5 points)
        if pcr < 0.8:
            score += 5   # More calls than puts = bullish

        # Cap score at 100
        return min(max(score, 0), 100)

    @staticmethod
    def _calculate_bearish_score(rsi: float, ema9: float, ema50: float, macd_hist: float,
                                 current_price: float, vwap: float, trend: str, pcr: float) -> float:
        """Calculate bearish bias score (0-100)"""
        score = 0

        # RSI component (0-20 points)
        if rsi > 70:
            score += 20  # Overbought, likely to pullback
        elif rsi > 50:
            score += 10  # Losing momentum
        elif rsi > 30:
            score += 5   # Still okay
        # Under 30 is oversold, no points

        # EMA component (0-25 points)
        if ema9 < ema50:
            score += 25  # Strong bearish structure (death cross)
        elif ema9 < ema50 * 1.01:
            score += 15  # Close to death cross
        else:
            score -= 10  # Bullish structure

        # MACD component (0-20 points)
        if macd_hist < 0:
            score += 20  # Negative momentum
        elif macd_hist < 10:
            score += 5   # Just started turning positive
        # Else positive momentum

        # Price vs VWAP (0-15 points)
        if current_price < vwap:
            score += 15  # Below VWAP = institutional selling
        elif current_price < vwap * 1.01:
            score += 5   # Close to VWAP
        # Above VWAP is bullish

        # Trend component (0-15 points)
        if trend == 'BEARISH':
            score += 15  # Clear downtrend
        elif 'BEARISH' in trend:
            score += 10
        # Bullish or neutral gets 0

        # PCR component (0-5 points)
        if pcr > 1.2:
            score += 5   # More puts than calls = bearish

        # Cap score at 100
        return min(max(score, 0), 100)
