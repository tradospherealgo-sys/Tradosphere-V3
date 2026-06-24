"""
Claude AI Service - Trading Analysis using Anthropic API
Provides intelligent market analysis, signal validation, and trading recommendations
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional


class ClaudeAIService:
    """Service for Claude AI-powered trading analysis"""

    MODEL = "claude-3-5-sonnet-20241022"
    API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    @staticmethod
    def analyze_market_data(symbol: str, price: float, change_percent: float,
                           technical_data: Dict, options_data: Dict = None) -> Dict:
        """Analyze market data using Claude AI"""
        if not ClaudeAIService.API_KEY:
            return ClaudeAIService._get_fallback_analysis(symbol, price, change_percent)

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=ClaudeAIService.API_KEY)

            prompt = f"""
            Analyze the following trading opportunity for {symbol}:

            Current Price: ₹{price:.2f}
            Change: {change_percent:+.2f}%
            Technical Data: {json.dumps(technical_data, indent=2)}
            {f'Options Data: {json.dumps(options_data, indent=2)}' if options_data else ''}

            Provide:
            1. Market sentiment (bullish/bearish/neutral)
            2. Key support and resistance levels
            3. Trading recommendation (BUY/SELL/HOLD)
            4. Risk/Reward ratio
            5. Entry and exit points
            6. Confidence level (0-100)

            Format as JSON.
            """

            message = client.messages.create(
                model=ClaudeAIService.MODEL,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # Parse JSON from response
            try:
                analysis = json.loads(response_text)
            except:
                analysis = {
                    "sentiment": "neutral",
                    "recommendation": "HOLD",
                    "confidence": 50,
                    "analysis": response_text
                }

            return {
                "status": "success",
                "symbol": symbol,
                "analysis": analysis,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "Claude AI"
            }

        except Exception as e:
            print(f"Claude API error: {e}")
            return ClaudeAIService._get_fallback_analysis(symbol, price, change_percent)

    @staticmethod
    def validate_signal(signal_data: Dict) -> Dict:
        """Validate a trading signal using Claude AI"""
        if not ClaudeAIService.API_KEY:
            return ClaudeAIService._get_fallback_validation(signal_data)

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=ClaudeAIService.API_KEY)

            prompt = f"""
            Validate this trading signal:

            Signal Data: {json.dumps(signal_data, indent=2)}

            Evaluate:
            1. Signal validity (0-100% confidence)
            2. Risk assessment
            3. Historical success rate for similar signals
            4. Recommended position size
            5. Alternative strategies

            Format as JSON.
            """

            message = client.messages.create(
                model=ClaudeAIService.MODEL,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            try:
                validation = json.loads(response_text)
            except:
                validation = {"analysis": response_text}

            return {
                "status": "success",
                "validation": validation,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return ClaudeAIService._get_fallback_validation(signal_data)

    @staticmethod
    def _get_fallback_analysis(symbol: str, price: float, change_percent: float) -> Dict:
        """Fallback analysis when Claude API is unavailable"""
        sentiment = "bullish" if change_percent > 0 else "bearish" if change_percent < -1 else "neutral"

        return {
            "status": "success",
            "symbol": symbol,
            "analysis": {
                "sentiment": sentiment,
                "recommendation": "BUY" if sentiment == "bullish" else "SELL" if sentiment == "bearish" else "HOLD",
                "confidence": abs(change_percent),
                "support": round(price * 0.98, 2),
                "resistance": round(price * 1.02, 2),
                "entry": round(price, 2),
                "target": round(price * 1.02, 2) if sentiment == "bullish" else round(price * 0.98, 2),
                "stoploss": round(price * 0.95, 2) if sentiment == "bullish" else round(price * 1.05, 2),
                "risk_reward_ratio": 2.0,
                "note": "Generated using fallback model (Claude API unavailable)"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "source": "Fallback Model"
        }

    @staticmethod
    def _get_fallback_validation(signal_data: Dict) -> Dict:
        """Fallback validation when Claude API is unavailable"""
        return {
            "status": "success",
            "validation": {
                "confidence": 60,
                "risk_assessment": "MEDIUM",
                "recommended_position_size": "1-2% of portfolio",
                "note": "Generated using fallback model (Claude API unavailable)"
            },
            "timestamp": datetime.utcnow().isoformat()
        }


if __name__ == "__main__":
    # Test Claude AI Service
    print("✅ Claude AI Service Ready")
    result = ClaudeAIService.analyze_market_data(
        "NIFTY",
        24000,
        3.5,
        {"EMA": "bullish", "RSI": 65, "MACD": "positive"}
    )
    print(json.dumps(result, indent=2))
