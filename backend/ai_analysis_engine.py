"""
AI Analysis Engine - Generate intelligent market insights
Analyzes all market data to provide recommendations and insights
"""

from typing import Dict, List, Optional
from datetime import datetime

class AIAnalysisEngine:
    """
    AI-powered market analysis engine
    Provides insights, recommendations, and sentiment analysis
    """

    @staticmethod
    def analyze_market(market_data: Dict, options_data: Dict, technical_data: Dict, signals: List[Dict], symbol: str = 'NIFTY') -> Dict:
        """
        Comprehensive AI analysis of market conditions

        Args:
            market_data: Live market prices and OHLC
            options_data: Options chain with PCR and Max Pain
            technical_data: Technical indicators
            signals: Generated trade signals
            symbol: Trading symbol

        Returns:
            Dict with comprehensive market analysis and insights
        """
        try:
            # Extract data
            current_price = market_data.get('current_price', 0)
            rsi = technical_data.get('indicators', {}).get('rsi', 50)
            ema9 = technical_data.get('indicators', {}).get('ema_9', 0)
            ema50 = technical_data.get('indicators', {}).get('ema_50', 0)
            macd_hist = technical_data.get('macd', {}).get('histogram', 0)
            vwap = technical_data.get('indicators', {}).get('vwap', 0)
            trend = technical_data.get('trend', 'NEUTRAL')
            momentum = technical_data.get('momentum', 'NEUTRAL')

            pcr = options_data.get('pcr', 1.0)
            max_pain = options_data.get('max_pain', current_price)

            # Calculate market bias
            market_bias = AIAnalysisEngine._calculate_market_bias(
                rsi, ema9, ema50, macd_hist, current_price, vwap, trend, pcr
            )

            # Calculate risk level
            risk_level = AIAnalysisEngine._calculate_risk_level(
                rsi, trend, pcr, abs(current_price - max_pain) / current_price
            )

            # Generate market insights
            insights = AIAnalysisEngine._generate_insights(
                market_bias, risk_level, rsi, ema9, ema50, pcr, current_price, max_pain, trend
            )

            # Generate recommendation
            recommendation = AIAnalysisEngine._generate_recommendation(
                market_bias, risk_level, rsi, trend, signals
            )

            # Calculate confidence score
            confidence_score = AIAnalysisEngine._calculate_confidence(
                market_bias, risk_level, len(signals)
            )

            # Analyze institutional activity
            institutional_activity = AIAnalysisEngine._analyze_institutional_activity(
                pcr, current_price, max_pain, vwap
            )

            # Analyze volatility
            volatility_info = AIAnalysisEngine._analyze_volatility(rsi, technical_data.get('bollinger_bands', {}))

            # Generate support/resistance
            support_resistance = AIAnalysisEngine._calculate_support_resistance(
                current_price, max_pain, ema9, ema50, vwap
            )

            # Determine best trading strategy
            best_strategy = AIAnalysisEngine._determine_strategy(market_bias, volatility_info, pcr)

            return {
                "status": "success",
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "market_bias": market_bias,
                "risk_level": risk_level,
                "confidence_score": confidence_score,
                "insights": insights,
                "recommendation": recommendation,
                "institutional_activity": institutional_activity,
                "volatility": volatility_info,
                "support_resistance": support_resistance,
                "best_strategy": best_strategy,
                "key_levels": {
                    "current_price": round(current_price, 2),
                    "max_pain": round(max_pain, 2),
                    "vwap": round(vwap, 2),
                    "ema_9": round(ema9, 2),
                    "ema_50": round(ema50, 2)
                },
                "market_indicators": {
                    "rsi": rsi,
                    "trend": trend,
                    "momentum": momentum,
                    "pcr": round(pcr, 2)
                },
                "signal_summary": {
                    "total_signals": len(signals),
                    "bullish_signals": len([s for s in signals if s['direction'] == 'BUY']),
                    "bearish_signals": len([s for s in signals if s['direction'] == 'SELL']),
                    "avg_confidence": round(sum([s['confidence'] for s in signals]) / len(signals), 1) if signals else 0
                }
            }

        except Exception as e:
            print(f"AI Analysis error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    @staticmethod
    def _calculate_market_bias(rsi: float, ema9: float, ema50: float, macd_hist: float,
                               current_price: float, vwap: float, trend: str, pcr: float) -> Dict:
        """Calculate overall market bias"""
        bias_score = 0

        # RSI component
        if rsi > 70:
            bias_score -= 20
        elif rsi > 60:
            bias_score -= 10
        elif rsi < 30:
            bias_score += 20
        elif rsi < 40:
            bias_score += 10

        # EMA component
        if ema9 > ema50:
            bias_score += 25
        else:
            bias_score -= 25

        # MACD component
        if macd_hist > 0:
            bias_score += 15
        else:
            bias_score -= 15

        # Price vs VWAP
        if current_price > vwap:
            bias_score += 15
        else:
            bias_score -= 15

        # Trend component
        if trend == 'BULLISH':
            bias_score += 20
        elif trend == 'BEARISH':
            bias_score -= 20

        # PCR component
        if pcr < 0.9:
            bias_score += 10
        elif pcr > 1.3:
            bias_score -= 10

        # Determine bias
        if bias_score > 40:
            bias_type = "STRONG BULLISH"
            emoji = "📈"
            color = "green"
        elif bias_score > 10:
            bias_type = "MILDLY BULLISH"
            emoji = "↗️"
            color = "green"
        elif bias_score < -40:
            bias_type = "STRONG BEARISH"
            emoji = "📉"
            color = "red"
        elif bias_score < -10:
            bias_type = "MILDLY BEARISH"
            emoji = "↘️"
            color = "red"
        else:
            bias_type = "NEUTRAL"
            emoji = "➡️"
            color = "gray"

        return {
            "type": bias_type,
            "emoji": emoji,
            "color": color,
            "score": bias_score,
            "strength": min(max(abs(bias_score) / 50, 0), 1)  # 0-1 scale
        }

    @staticmethod
    def _calculate_risk_level(rsi: float, trend: str, pcr: float, distance_to_max_pain: float) -> Dict:
        """Calculate overall risk level"""
        risk_score = 0

        # RSI risk
        if rsi > 80 or rsi < 20:
            risk_score += 30  # Very risky
        elif rsi > 70 or rsi < 30:
            risk_score += 15  # Moderate risk

        # Trend confirmation risk
        if trend == 'NEUTRAL':
            risk_score += 20

        # PCR risk
        if pcr > 1.5 or pcr < 0.7:
            risk_score += 15  # Extreme OI distribution

        # Distance to max pain risk
        if distance_to_max_pain < 0.5:
            risk_score += 20  # Price too close to max pain

        # Determine risk level
        if risk_score > 60:
            level = "HIGH"
            description = "Market highly volatile, wide stop-losses needed"
            color = "red"
        elif risk_score > 30:
            level = "MEDIUM"
            description = "Moderate volatility, standard risk management"
            color = "yellow"
        else:
            level = "LOW"
            description = "Stable conditions, controlled risk environment"
            color = "green"

        return {
            "level": level,
            "score": risk_score,
            "description": description,
            "color": color
        }

    @staticmethod
    def _generate_insights(bias: Dict, risk: Dict, rsi: float, ema9: float, ema50: float,
                          pcr: float, price: float, max_pain: float, trend: str) -> List[str]:
        """Generate market insights"""
        insights = []

        # RSI insights
        if rsi > 75:
            insights.append(f"🔴 RSI at {rsi:.1f} - Overbought. Potential pullback likely.")
        elif rsi < 25:
            insights.append(f"🟢 RSI at {rsi:.1f} - Oversold. Bounce opportunity present.")
        elif rsi > 60:
            insights.append(f"🟡 RSI at {rsi:.1f} - Strong momentum but caution near 70.")

        # EMA insights
        if ema9 > ema50 * 1.02:
            insights.append(f"📈 Golden Cross confirmed (EMA 9 > EMA 50). Strong uptrend intact.")
        elif ema9 < ema50 * 0.98:
            insights.append(f"📉 Death Cross detected (EMA 9 < EMA 50). Downtrend confirmed.")

        # PCR insights
        if pcr > 1.4:
            insights.append(f"📊 High PCR ({pcr:.2f}) indicates strong put buildup. Reversal potential.")
        elif pcr < 0.8:
            insights.append(f"📊 Low PCR ({pcr:.2f}) shows call dominance. Upside potential.")

        # Max pain insights
        distance_pct = abs(price - max_pain) / price * 100
        if distance_pct < 1:
            insights.append(f"🎯 Price within 1% of Max Pain ({max_pain:.0f}). Major support/resistance zone.")
        elif distance_pct < 2:
            insights.append(f"🎯 Price approaching Max Pain. Market structure important.")

        # Volatility insights
        if rsi > 70 or rsi < 30:
            insights.append(f"⚡ Extreme volatility detected. Use wider stop-losses.")

        # Trend insights
        if trend == 'BULLISH':
            insights.append("✅ Uptrend active. Prefer BUY strategies on dips.")
        elif trend == 'BEARISH':
            insights.append("❌ Downtrend active. Prefer SELL strategies on rallies.")

        return insights

    @staticmethod
    def _generate_recommendation(bias: Dict, risk: Dict, rsi: float, trend: str, signals: List[Dict]) -> Dict:
        """Generate AI recommendation"""
        bias_type = bias['type']
        risk_level = risk['level']

        # Determine action
        if 'BULLISH' in bias_type and risk_level != 'HIGH':
            action = "BUY"
            action_emoji = "🟢"
            action_color = "green"
            timeframe = "Short-term upside bias"
        elif 'BEARISH' in bias_type and risk_level != 'HIGH':
            action = "SELL"
            action_emoji = "🔴"
            action_color = "red"
            timeframe = "Short-term downside bias"
        elif risk_level == 'HIGH':
            action = "WAIT"
            action_emoji = "⏸️"
            action_color = "yellow"
            timeframe = "High volatility - wait for clarity"
        else:
            action = "NEUTRAL"
            action_emoji = "➡️"
            action_color = "gray"
            timeframe = "No clear direction"

        # Generate detailed recommendation
        if signals:
            top_signal = signals[0]
            signal_type = top_signal['type']
            strike = top_signal['strike']
            recommendation_text = f"{action_emoji} {action}: Use {signal_type} options near {strike} strike. {timeframe}."
        else:
            recommendation_text = f"{action_emoji} {action}: {timeframe}."

        # Add risk management note
        if risk_level == 'HIGH':
            risk_note = "⚠️ Use wider stops due to high volatility."
        elif risk_level == 'MEDIUM':
            risk_note = "📌 Use standard risk management (2% rule)."
        else:
            risk_note = "✅ Favorable risk environment. Standard setup valid."

        return {
            "action": action,
            "emoji": action_emoji,
            "color": action_color,
            "timeframe": timeframe,
            "recommendation": recommendation_text,
            "risk_note": risk_note,
            "confidence_reason": f"Based on {bias['type']} bias with {risk_level} risk. {trend} trend confirmed."
        }

    @staticmethod
    def _calculate_confidence(bias: Dict, risk: Dict, signal_count: int) -> float:
        """Calculate overall analysis confidence"""
        confidence = 50  # Base 50%

        # Bias strength adds up to 40%
        confidence += bias['strength'] * 40

        # Risk assessment
        if risk['level'] == 'LOW':
            confidence += 10
        elif risk['level'] == 'HIGH':
            confidence -= 5

        # Signal alignment
        if signal_count >= 2:
            confidence += 5
        elif signal_count == 0:
            confidence -= 10

        return min(max(confidence, 0), 100)

    @staticmethod
    def _analyze_institutional_activity(pcr: float, price: float, max_pain: float, vwap: float) -> Dict:
        """Analyze institutional activity"""
        # Determine institutional bias
        if price > vwap:
            institutional_bias = "Buying"
            bias_emoji = "🟢"
        else:
            institutional_bias = "Selling"
            bias_emoji = "🔴"

        # PCR tells us what institutions are protecting
        if pcr > 1.2:
            protection = "Protecting downside (high put OI)"
            outlook = "Bullish bias"
        elif pcr < 0.9:
            protection = "Protecting upside (high call OI)"
            outlook = "Bearish bias"
        else:
            protection = "Balanced (equal protection)"
            outlook = "Neutral outlook"

        # Distance to max pain
        distance = abs(price - max_pain) / price * 100
        if distance < 1:
            max_pain_status = "Critical - Major support/resistance"
        elif distance < 3:
            max_pain_status = "Important - Watch this level"
        else:
            max_pain_status = "Far - Not immediate concern"

        return {
            "bias": institutional_bias,
            "emoji": bias_emoji,
            "description": f"Institutions are {institutional_bias.lower()} at current price above VWAP",
            "protection": protection,
            "outlook": outlook,
            "max_pain_status": max_pain_status,
            "activity_level": "High" if abs(pcr - 1.0) > 0.3 else "Balanced"
        }

    @staticmethod
    def _analyze_volatility(rsi: float, bollinger_bands: Dict) -> Dict:
        """Analyze volatility conditions"""
        # RSI-based volatility
        if rsi > 75 or rsi < 25:
            rsi_volatility = "Very High"
            rsi_color = "red"
        elif rsi > 65 or rsi < 35:
            rsi_volatility = "High"
            rsi_color = "orange"
        else:
            rsi_volatility = "Normal"
            rsi_color = "green"

        # Bollinger Band-based volatility
        bb_range = bollinger_bands.get('upper_band', 0) - bollinger_bands.get('lower_band', 0)
        position = bollinger_bands.get('position', 'between')

        if position in ['above', 'below']:
            bb_volatility = "High expansion"
            bb_status = f"Trading at {position} band - high volatility"
        else:
            bb_volatility = "Normal"
            bb_status = "Trading within bands - normal range"

        return {
            "rsi_level": rsi_volatility,
            "rsi_color": rsi_color,
            "bollinger_status": bb_status,
            "overall_assessment": f"Overall: {rsi_volatility}. Trade appropriately with wider stops.",
            "recommended_strategy": "Mean reversion" if position in ['above', 'below'] else "Trend following"
        }

    @staticmethod
    def _calculate_support_resistance(price: float, max_pain: float, ema9: float, ema50: float, vwap: float) -> Dict:
        """Calculate support and resistance levels"""
        levels = {
            "Immediate Resistance": ema9,
            "Intermediate Resistance": ema50,
            "Max Pain (Important)": max_pain,
            "VWAP Support": vwap,
            "Intermediate Support": ema50 * 0.98,
            "Immediate Support": ema9 * 0.98
        }

        # Sort and identify nearest
        nearest_resistance = None
        nearest_support = None

        for level_name, level_value in levels.items():
            if level_value > price and (nearest_resistance is None or level_value < nearest_resistance):
                nearest_resistance = level_value
            elif level_value < price and (nearest_support is None or level_value > nearest_support):
                nearest_support = level_value

        # Build recommendation
        if nearest_support and nearest_resistance:
            recommendation = f"Trade between {round(nearest_support, 2)} and {round(nearest_resistance, 2)}"
        else:
            recommendation = "Use key levels for trade setup"

        return {
            "nearest_resistance": round(nearest_resistance, 2) if nearest_resistance else "N/A",
            "nearest_support": round(nearest_support, 2) if nearest_support else "N/A",
            "key_levels": {
                name: round(value, 2) for name, value in levels.items()
            },
            "recommendation": recommendation
        }

    @staticmethod
    def _determine_strategy(bias: Dict, volatility: Dict, pcr: float) -> Dict:
        """Determine best trading strategy"""
        bias_type = bias['type']
        vol_strategy = volatility['recommended_strategy']

        if 'BULLISH' in bias_type:
            if vol_strategy == "Mean reversion":
                strategy = "Aggressive BUY - Call spreads preferred"
            else:
                strategy = "Sustained BUY - Call options or long stock"
        elif 'BEARISH' in bias_type:
            if vol_strategy == "Mean reversion":
                strategy = "Aggressive SELL - Put spreads preferred"
            else:
                strategy = "Sustained SELL - Put options or short"
        else:
            strategy = "Range trading - Iron Condor or Straddle"

        return {
            "recommended": strategy,
            "timeframe": "5-15 min trades" if vol_strategy == "Mean reversion" else "Swing trades (1-3 days)",
            "risk_management": "Use 2% position sizing",
            "entry_trigger": "On dips" if 'BUY' in strategy else "On rallies",
            "profit_target": "1.5-2% daily",
            "stop_loss": "0.75-1% from entry"
        }
