"""
Claude AI Service - Trading Analysis using Anthropic API
Provides intelligent market analysis, signal validation, and trading recommendations
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ClaudeAIService:
    """Service for Claude AI-powered trading analysis"""

    MODEL = "claude-3-5-sonnet-20241022"
    API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    @staticmethod
    def analyze_market_data(symbol: str, price: float, change_percent: float,
                           technical_data: Dict, options_data: Dict = None) -> Dict:
        """Analyze market data using Claude AI"""
        if not ClaudeAIService.API_KEY:
            logger.warning(f"Claude AI API key not configured, returning service unavailable")
            return {
                "status": "error",
                "error": "AI analysis service is temporarily unavailable",
                "code": "AI_SERVICE_UNAVAILABLE",
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat()
            }

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
            logger.error(f"Claude API error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": "AI analysis service is temporarily unavailable",
                "code": "AI_SERVICE_ERROR",
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat()
            }

    @staticmethod
    def validate_signal(signal_data: Dict) -> Dict:
        """Validate a trading signal using Claude AI"""
        if not ClaudeAIService.API_KEY:
            logger.warning("Claude AI API key not configured, returning service unavailable")
            return {
                "status": "error",
                "error": "AI validation service is temporarily unavailable",
                "code": "AI_SERVICE_UNAVAILABLE",
                "timestamp": datetime.utcnow().isoformat()
            }

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
            logger.error(f"Claude validation error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": "AI validation service is temporarily unavailable",
                "code": "AI_SERVICE_ERROR",
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
