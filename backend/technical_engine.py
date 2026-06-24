"""
Technical Engine - Calculate technical indicators and detect patterns
Processes candlestick data and generates technical analysis
"""

from typing import Dict, List, Optional
import math

class TechnicalEngine:
    """
    Technical analysis engine for market data
    Calculates RSI, EMA, VWAP, detects trends and breakouts
    """

    def __init__(self):
        pass

    @staticmethod
    def calculate_rsi(closes: List[float], period: int = 14) -> Optional[float]:
        """
        Calculate Relative Strength Index (RSI)

        Args:
            closes: List of closing prices
            period: RSI period (default 14)

        Returns:
            RSI value (0-100) or None if insufficient data
        """
        if len(closes) < period:
            return None

        # Calculate gains and losses
        gains = 0.0
        losses = 0.0

        for i in range(1, period + 1):
            change = closes[-i] - closes[-(i + 1)]
            if change > 0:
                gains += change
            else:
                losses += abs(change)

        # Calculate averages
        avg_gain = gains / period
        avg_loss = losses / period

        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 0.0

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return round(rsi, 2)

    @staticmethod
    def calculate_ema(closes: List[float], period: int = 20) -> Optional[float]:
        """
        Calculate Exponential Moving Average (EMA)

        Args:
            closes: List of closing prices
            period: EMA period (default 20)

        Returns:
            EMA value or None if insufficient data
        """
        if len(closes) < period:
            return None

        # Calculate simple average for first period
        sma = sum(closes[-period:]) / period

        # Calculate multiplier
        multiplier = 2 / (period + 1)

        # Calculate EMA
        ema = sma
        for i in range(period, len(closes)):
            ema = closes[-len(closes) + i] * multiplier + ema * (1 - multiplier)

        return round(ema, 2)

    @staticmethod
    def calculate_vwap(candles: List[Dict]) -> Optional[float]:
        """
        Calculate Volume-Weighted Average Price (VWAP)

        Args:
            candles: List of candle dicts with high, low, close, volume

        Returns:
            VWAP value or None if no candles
        """
        if not candles or len(candles) == 0:
            return None

        cum_volume = 0.0
        cum_tp_volume = 0.0

        for candle in candles:
            # Typical Price = (High + Low + Close) / 3
            tp = (candle.get("high", 0) + candle.get("low", 0) + candle.get("close", 0)) / 3
            volume = candle.get("volume", 0)

            cum_tp_volume += tp * volume
            cum_volume += volume

        if cum_volume == 0:
            return None

        vwap = cum_tp_volume / cum_volume
        return round(vwap, 2)

    @staticmethod
    def detect_trend(closes: List[float], ema_period: int = 20) -> str:
        """
        Detect current trend based on price vs EMA

        Args:
            closes: List of closing prices
            ema_period: EMA period for trend detection

        Returns:
            "BULLISH", "BEARISH", or "NEUTRAL"
        """
        if len(closes) < ema_period:
            return "NEUTRAL"

        current_price = closes[-1]
        ema = TechnicalEngine.calculate_ema(closes, ema_period)

        if ema is None:
            return "NEUTRAL"

        # Trend classification
        if current_price > ema * 1.01:  # More than 1% above EMA
            return "BULLISH"
        elif current_price < ema * 0.99:  # More than 1% below EMA
            return "BEARISH"
        else:
            return "NEUTRAL"

    @staticmethod
    def detect_momentum(rsi: Optional[float]) -> str:
        """
        Detect momentum based on RSI

        Args:
            rsi: RSI value (0-100)

        Returns:
            "STRONG BULLISH", "BULLISH", "NEUTRAL", "BEARISH", "STRONG BEARISH"
        """
        if rsi is None:
            return "NEUTRAL"

        if rsi > 70:
            return "STRONG BULLISH"
        elif rsi > 55:
            return "BULLISH"
        elif rsi < 30:
            return "STRONG BEARISH"
        elif rsi < 45:
            return "BEARISH"
        else:
            return "NEUTRAL"

    @staticmethod
    def calculate_macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict]:
        """
        Calculate MACD (Moving Average Convergence Divergence)

        Args:
            closes: List of closing prices
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line EMA period (default 9)

        Returns:
            Dict with MACD, signal line, and histogram or None if insufficient data
        """
        if len(closes) < slow:
            return None

        # Calculate fast and slow EMAs
        ema_fast = TechnicalEngine.calculate_ema(closes, fast)
        ema_slow = TechnicalEngine.calculate_ema(closes, slow)

        if ema_fast is None or ema_slow is None:
            return None

        # MACD line = fast EMA - slow EMA
        macd_line = ema_fast - ema_slow

        # Calculate signal line (EMA of MACD)
        # Build MACD array for last 'signal' periods
        macd_values = []
        for i in range(len(closes) - signal, len(closes)):
            if i >= slow - 1:
                ema_f = TechnicalEngine.calculate_ema(closes[:i + 1], fast)
                ema_s = TechnicalEngine.calculate_ema(closes[:i + 1], slow)
                if ema_f and ema_s:
                    macd_values.append(ema_f - ema_s)

        # Signal line is EMA of MACD values
        if len(macd_values) >= signal:
            signal_line = sum(macd_values[-signal:]) / signal  # Simple for last signal period
        else:
            signal_line = macd_line

        # Histogram = MACD - Signal
        histogram = macd_line - signal_line

        return {
            "macd": round(macd_line, 4),
            "signal_line": round(signal_line, 4),
            "histogram": round(histogram, 4)
        }

    @staticmethod
    def calculate_bollinger_bands(closes: List[float], period: int = 20, std_dev: float = 2.0) -> Optional[Dict]:
        """
        Calculate Bollinger Bands

        Args:
            closes: List of closing prices
            period: Period for SMA (default 20)
            std_dev: Standard deviations (default 2.0)

        Returns:
            Dict with upper band, middle band (SMA), lower band or None
        """
        if len(closes) < period:
            return None

        # Middle band = SMA
        recent = closes[-period:]
        sma = sum(recent) / period

        # Calculate standard deviation
        variance = sum((x - sma) ** 2 for x in recent) / period
        std_deviation = math.sqrt(variance)

        # Bands
        upper_band = sma + (std_dev * std_deviation)
        lower_band = sma - (std_dev * std_deviation)
        current_price = closes[-1]

        # Position relative to bands
        if current_price > upper_band:
            position = "above_upper"
        elif current_price < lower_band:
            position = "below_lower"
        else:
            position = "between"

        return {
            "upper_band": round(upper_band, 2),
            "middle_band": round(sma, 2),
            "lower_band": round(lower_band, 2),
            "std_dev": round(std_deviation, 4),
            "position": position,
            "current_price": round(current_price, 2)
        }

    @staticmethod
    def detect_ema_crossovers(closes: List[float], fast_period: int = 9, slow_period: int = 50) -> Optional[Dict]:
        """
        Detect EMA crossovers (Golden Cross / Death Cross)

        Args:
            closes: List of closing prices
            fast_period: Fast EMA period (default 9)
            slow_period: Slow EMA period (default 50)

        Returns:
            Dict with crossover information
        """
        if len(closes) < slow_period:
            return None

        # Current EMAs
        ema_fast = TechnicalEngine.calculate_ema(closes, fast_period)
        ema_slow = TechnicalEngine.calculate_ema(closes, slow_period)

        if ema_fast is None or ema_slow is None:
            return None

        # Previous EMAs (one bar back)
        if len(closes) >= slow_period + 1:
            ema_fast_prev = TechnicalEngine.calculate_ema(closes[:-1], fast_period)
            ema_slow_prev = TechnicalEngine.calculate_ema(closes[:-1], slow_period)
        else:
            ema_fast_prev = ema_fast
            ema_slow_prev = ema_slow

        # Detect crossover
        crossover = None
        if ema_fast_prev and ema_slow_prev:
            if ema_fast_prev <= ema_slow_prev and ema_fast > ema_slow:
                crossover = "GOLDEN_CROSS"  # Bullish
            elif ema_fast_prev >= ema_slow_prev and ema_fast < ema_slow:
                crossover = "DEATH_CROSS"  # Bearish

        # Current relationship
        if ema_fast > ema_slow:
            relationship = "above"  # Bullish
        elif ema_fast < ema_slow:
            relationship = "below"  # Bearish
        else:
            relationship = "equal"

        return {
            "ema_fast": round(ema_fast, 2),
            "ema_slow": round(ema_slow, 2),
            "relationship": relationship,
            "crossover": crossover,
            "crossover_type": "BULLISH" if crossover == "GOLDEN_CROSS" else "BEARISH" if crossover == "DEATH_CROSS" else None
        }

    @staticmethod
    def detect_breakout(candles: List[Dict], lookback: int = 20) -> Optional[Dict]:
        """
        Detect potential breakouts

        Args:
            candles: List of candle dicts
            lookback: Number of candles to look back for resistance/support

        Returns:
            Dict with breakout info or None
        """
        if len(candles) < lookback:
            return None

        recent_candles = candles[-lookback:]

        # Find resistance and support
        highs = [c.get("high", 0) for c in recent_candles]
        lows = [c.get("low", 0) for c in recent_candles]

        resistance = max(highs)
        support = min(lows)

        current_price = candles[-1].get("close", 0)
        current_high = candles[-1].get("high", 0)

        # Detect breakout
        is_breakout = False
        breakout_type = None

        if current_high > resistance:
            is_breakout = True
            breakout_type = "UPSIDE"
        elif current_price < support:
            is_breakout = True
            breakout_type = "DOWNSIDE"

        if is_breakout:
            return {
                "breakout": True,
                "type": breakout_type,
                "resistance": round(resistance, 2),
                "support": round(support, 2),
                "current_price": round(current_price, 2)
            }

        return {"breakout": False, "resistance": round(resistance, 2), "support": round(support, 2)}

    @staticmethod
    def analyze(candles: List[Dict]) -> Dict:
        """
        Comprehensive technical analysis with all indicators

        Args:
            candles: List of candle dicts (must have: open, high, low, close, volume)

        Returns:
            Dict with complete technical analysis including all indicators
        """
        if not candles or len(candles) < 26:
            return {
                "status": "insufficient_data",
                "message": "Need at least 26 candles for complete analysis (MACD requires 26)",
                "candles_provided": len(candles) if candles else 0
            }

        # Extract closes and calculate indicators
        closes = [c.get("close", 0) for c in candles]

        # Basic indicators
        rsi = TechnicalEngine.calculate_rsi(closes, 14)
        ema9 = TechnicalEngine.calculate_ema(closes, 9)
        ema20 = TechnicalEngine.calculate_ema(closes, 20)
        ema50 = TechnicalEngine.calculate_ema(closes, 50) if len(closes) >= 50 else None
        vwap = TechnicalEngine.calculate_vwap(candles)

        # Advanced indicators
        macd_data = TechnicalEngine.calculate_macd(closes, 12, 26, 9)
        bb_data = TechnicalEngine.calculate_bollinger_bands(closes, 20, 2.0)
        ema_crossover = TechnicalEngine.detect_ema_crossovers(closes, 9, 50)

        # Detect patterns
        trend = TechnicalEngine.detect_trend(closes, 20)
        momentum = TechnicalEngine.detect_momentum(rsi)
        breakout = TechnicalEngine.detect_breakout(candles, 20)

        # Determine setup
        setup = "RANGE_BOUND"
        if breakout.get("breakout"):
            setup = f"BREAKOUT_{breakout['type']}"
        elif trend == "BULLISH" and momentum in ["BULLISH", "STRONG BULLISH"]:
            setup = "STRONG_UPTREND"
        elif trend == "BEARISH" and momentum in ["BEARISH", "STRONG BEARISH"]:
            setup = "STRONG_DOWNTREND"

        # Current values
        current_price = closes[-1]

        # EMA Crossover signal strength
        ema_crossover_signal = "NONE"
        if ema_crossover and ema_crossover.get("crossover"):
            ema_crossover_signal = ema_crossover["crossover"]

        return {
            "status": "success",
            "trend": trend,
            "momentum": momentum,
            "setup": setup,
            "indicators": {
                "rsi": rsi,
                "ema_9": ema9,
                "ema_20": ema20,
                "ema_50": ema50,
                "vwap": vwap,
                "current_price": round(current_price, 2)
            },
            "macd": macd_data if macd_data else {},
            "bollinger_bands": bb_data if bb_data else {},
            "ema_crossover": ema_crossover if ema_crossover else {},
            "price_vs_indicators": {
                "price_vs_ema9": "above" if current_price > (ema9 or 0) else "below",
                "price_vs_ema20": "above" if current_price > (ema20 or 0) else "below",
                "price_vs_ema50": "above" if current_price > (ema50 or 0) else "below" if ema50 else "N/A",
                "price_vs_vwap": "above" if current_price > (vwap or 0) else "below"
            },
            "breakout": breakout,
            "ema_crossover_signal": ema_crossover_signal
        }
