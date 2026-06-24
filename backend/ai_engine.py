"""
AI Explanation Layer - Generates human-readable market analysis and explanations
Reads technical analysis, options analysis, and market conditions
"""

from typing import Dict, Optional, List
from datetime import datetime


class AIEngine:
    """
    AI engine for market analysis explanation
    Generates market summaries, trade explanations, and risk warnings
    """

    @staticmethod
    def generate_market_summary(technical_data: Dict, options_data: Dict) -> Dict:
        """
        Generate human-readable market summary

        Args:
            technical_data: Output from TechnicalEngine.analyze()
            options_data: Output from OptionsEngine.analyze()

        Returns:
            Dict with market summary and explanation
        """
        try:
            summary_points = []
            bias = "NEUTRAL"

            # Analyze technical data
            if technical_data and technical_data.get("status") == "success":
                trend = technical_data.get("trend", "NEUTRAL")
                momentum = technical_data.get("momentum", "NEUTRAL")
                setup = technical_data.get("setup", "RANGE_BOUND")
                rsi = technical_data.get("indicators", {}).get("rsi")
                ema20 = technical_data.get("indicators", {}).get("ema_20")
                vwap = technical_data.get("indicators", {}).get("vwap")
                current_price = technical_data.get("indicators", {}).get("current_price", 0)

                # Build technical summary
                if trend == "BULLISH":
                    summary_points.append("✓ Price is above key EMAs (bullish trend)")
                    bias = "BULLISH"
                elif trend == "BEARISH":
                    summary_points.append("✓ Price is below key EMAs (bearish trend)")
                    bias = "BEARISH"

                # Momentum analysis
                if "STRONG" in momentum:
                    summary_points.append(f"✓ RSI shows strong {momentum.lower()} momentum ({rsi})")
                elif momentum != "NEUTRAL":
                    summary_points.append(f"✓ RSI indicates {momentum.lower()} momentum ({rsi})")

                # VWAP analysis
                if current_price and vwap:
                    if current_price > vwap:
                        summary_points.append("✓ Price trading above VWAP (institutional support)")
                    else:
                        summary_points.append("✓ Price trading below VWAP (institutional resistance)")

                # Setup analysis
                if "BREAKOUT" in setup:
                    summary_points.append(f"✓ {setup} setup detected")

            # Analyze options data
            if options_data and options_data.get("status") == "success":
                # Handle both new and old format
                if isinstance(options_data.get("pcr"), dict):
                    pcr_value = options_data.get("pcr", {}).get("pcr", 1.0)
                    pcr_analysis = options_data.get("pcr", {})
                else:
                    pcr_value = options_data.get("pcr", 1.0)
                    pcr_analysis = {"pcr": pcr_value}

                pcr_bias = pcr_analysis.get("bias", "NEUTRAL")
                oi_trend = options_data.get("oi_analysis", {}).get("trend") or options_data.get("oi", {}).get("trend", "STABLE")
                volume_bias = options_data.get("volume_analysis", {}).get("volume_bias") or options_data.get("volume", {}).get("volume_bias", "BALANCED")
                support = options_data.get("support")
                resistance = options_data.get("resistance")
                max_pain = options_data.get("max_pain")

                # PCR analysis
                if pcr_value > 1.2:
                    summary_points.append(f"✓ High PCR {pcr_value:.2f} indicates put buying (bullish outlook)")
                    if bias != "BULLISH":
                        bias = "BULLISH"
                elif pcr_value < 0.8:
                    summary_points.append(f"✓ Low PCR {pcr_value:.2f} indicates call buying (bearish outlook)")
                    if bias != "BEARISH":
                        bias = "BEARISH"
                else:
                    summary_points.append(f"✓ PCR {pcr_value:.2f} shows neutral sentiment")

                # OI analysis
                if "BUILDUP" in oi_trend:
                    summary_points.append("✓ Option OI increasing (fresh positions)")
                elif "UNWINDING" in oi_trend:
                    summary_points.append("✓ Option OI decreasing (position exit)")

                # Volume bias
                if "CALL" in volume_bias:
                    summary_points.append("✓ Call volumes dominating (selling pressure)")
                elif "PUT" in volume_bias:
                    summary_points.append("✓ Put volumes dominating (support building)")

            # Determine overall bias from options if not from technical
            if bias == "NEUTRAL" and options_data:
                overall_bias = options_data.get("bias", "NEUTRAL")
                if overall_bias != "NEUTRAL":
                    bias = overall_bias

            # Create summary sentence
            summary_text = AIEngine._create_summary_text(bias, summary_points)

            return {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "bias": bias,
                "summary": summary_text,
                "points": summary_points,
                "confidence": min(len(summary_points) / 5 * 100, 95),  # Confidence based on number of signals
                "support": options_data.get("support") if options_data else None,
                "resistance": options_data.get("resistance") if options_data else None,
                "max_pain": options_data.get("max_pain") if options_data else None
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    @staticmethod
    def _create_summary_text(bias: str, points: List[str]) -> str:
        """Create human-readable summary text"""
        if not points:
            return f"Market shows {bias.lower()} bias but insufficient data for detailed analysis."

        if bias == "BULLISH":
            if len(points) >= 3:
                return f"Market is moderately bullish. {points[0]} and {points[1]} support upside potential."
            else:
                return f"Market bias is {bias.lower()}. {points[0]}"

        elif bias == "BEARISH":
            if len(points) >= 3:
                return f"Market is moderately bearish. {points[0]} and {points[1]} suggest downside risk."
            else:
                return f"Market bias is {bias.lower()}. {points[0]}"

        else:
            return f"Market remains neutral. {points[0]} but conviction is mixed."

    @staticmethod
    def generate_signal_explanation(signal_data: Dict, technical_data: Dict, options_data: Dict) -> Dict:
        """
        Generate explanation for a trading signal

        Args:
            signal_data: Signal details (entry, target, SL)
            technical_data: Technical analysis
            options_data: Options analysis

        Returns:
            Dict with signal explanation
        """
        try:
            reasons = []
            risks = []

            # Technical reasons
            if technical_data and technical_data.get("status") == "success":
                if technical_data.get("trend") == "BULLISH":
                    reasons.append("Price is above 20/50 EMA")

                rsi = technical_data.get("indicators", {}).get("rsi")
                if rsi and rsi > 50:
                    reasons.append(f"RSI at {rsi} shows momentum")

                if technical_data.get("setup") == "BREAKOUT_UPSIDE":
                    reasons.append("Breakout above resistance detected")

            # Options reasons
            if options_data and options_data.get("status") == "success":
                pcr = options_data.get("pcr", {}).get("pcr", 1.0)
                if pcr > 1.1:
                    reasons.append("Put-Call Ratio favors upside")

                oi = options_data.get("oi", {}).get("trend")
                if "BUILDUP" in oi:
                    reasons.append("Option OI buildup in calls")

            # Risk warnings
            if technical_data:
                rsi = technical_data.get("indicators", {}).get("rsi")
                if rsi and rsi > 70:
                    risks.append("RSI is overbought - watch for pullbacks")
                elif rsi and rsi < 30:
                    risks.append("RSI is oversold - risk of sharp bounce")

            if options_data:
                pcr = options_data.get("pcr", {}).get("pcr", 1.0)
                if pcr > 1.5:
                    risks.append("Extreme PCR levels - watch for reversal")

            return {
                "status": "success",
                "reasons": reasons,
                "risks": risks,
                "timestamp": datetime.utcnow().isoformat(),
                "note": "Signal valid as long as key technical levels hold"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    @staticmethod
    def generate_risk_warning(technical_data: Dict, options_data: Dict) -> Dict:
        """
        Generate risk assessment for current market conditions

        Args:
            technical_data: Technical analysis
            options_data: Options analysis

        Returns:
            Dict with risk assessment
        """
        try:
            risk_level = "MEDIUM"
            warnings = []
            precautions = []

            # Analyze volatility/momentum extremes
            if technical_data and technical_data.get("status") == "success":
                rsi = technical_data.get("indicators", {}).get("rsi")
                momentum = technical_data.get("momentum", "NEUTRAL")

                if rsi and (rsi > 80 or rsi < 20):
                    risk_level = "HIGH"
                    warnings.append("Extreme momentum - high risk of reversal")
                    precautions.append("Reduce position size or avoid new trades")

                elif rsi and (rsi > 70 or rsi < 30):
                    risk_level = "MEDIUM-HIGH"
                    warnings.append("Momentum is extreme - consolidation likely")
                    precautions.append("Use tighter stops or smaller positions")

            # Analyze options volatility
            if options_data and options_data.get("status") == "success":
                pcr = options_data.get("pcr", {}).get("pcr", 1.0)
                if pcr > 2.0 or pcr < 0.5:
                    warnings.append("PCR is at extreme levels")
                    precautions.append("Watch for potential reversal")

            return {
                "status": "success",
                "risk_level": risk_level,
                "warnings": warnings,
                "precautions": precautions,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
