"""
Real Signal Generator - Algorithmic Trading Signals
Generates real trading signals based on technical indicators
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class RealSignalGenerator:
    """Generate real trading signals based on technical analysis"""

    @staticmethod
    def generate_signal(
        symbol: str,
        price: float,
        technical_data: Dict,
        ai_confidence: float = 50
    ) -> Dict:
        """
        Generate real trading signal based on technical indicators
        
        Args:
            symbol: Trading symbol (e.g., 'NIFTY')
            price: Current price
            technical_data: Dict with EMA, RSI, MACD values
            ai_confidence: AI analysis confidence (0-100)
        
        Returns:
            Signal dict with BUY/SELL/HOLD recommendation
        """
        
        try:
            # Extract technical indicators
            ema_20 = float(technical_data.get('ema_20', price))
            ema_50 = float(technical_data.get('ema_50', price))
            ema_200 = float(technical_data.get('ema_200', price))
            rsi = float(technical_data.get('rsi', 50))
            macd = float(technical_data.get('macd', 0))
            macd_signal = float(technical_data.get('macd_signal', 0))
            
            # Calculate signals
            ema_signal = RealSignalGenerator._analyze_ema(price, ema_20, ema_50, ema_200)
            rsi_signal = RealSignalGenerator._analyze_rsi(rsi)
            macd_signal_result = RealSignalGenerator._analyze_macd(macd, macd_signal)
            
            # Combine signals
            signals = [ema_signal, rsi_signal, macd_signal_result]
            signal_counts = {
                'BUY': sum(1 for s in signals if s == 'BUY'),
                'SELL': sum(1 for s in signals if s == 'SELL'),
                'HOLD': sum(1 for s in signals if s == 'HOLD')
            }
            
            # Determine final signal
            if signal_counts['BUY'] >= 2:
                final_signal = 'BUY'
            elif signal_counts['SELL'] >= 2:
                final_signal = 'SELL'
            else:
                final_signal = 'HOLD'
            
            # F-12: this number is the agreement rate across the three
            # independent technical checks (EMA, RSI, MACD), blended with the AI
            # confidence input. It is NOT a calibrated probability of profit, so
            # it is surfaced as "signal agreement %", not raw "confidence".
            base_confidence = (signal_counts.get(final_signal, 0) / 3) * 100
            signal_agreement_pct = round(min((base_confidence + ai_confidence) / 2, 100), 0)

            # F-13: derive target/stop from ATR (volatility) computed from live
            # candles, not a fixed 2%. ATR adapts levels to the instrument's real
            # volatility. We use a 1.5x ATR stop and a 2:1 reward:risk target.
            # If ATR is unavailable we fall back to a percentage and label it.
            atr = technical_data.get('atr')
            entry_price = price
            levels_method = "atr"
            try:
                atr = float(atr) if atr is not None else None
            except (TypeError, ValueError):
                atr = None

            if atr and atr > 0:
                stop_distance = 1.5 * atr
                target_distance = 3.0 * atr  # 2:1 reward:risk
            else:
                levels_method = "percent_fallback"
                stop_distance = price * 0.02
                target_distance = price * 0.02

            if final_signal == 'BUY':
                target = price + target_distance
                stop_loss = price - stop_distance
            elif final_signal == 'SELL':
                target = price - target_distance
                stop_loss = price + stop_distance
            else:
                target = price
                stop_loss = price

            signal = {
                "symbol": symbol,
                "signal": final_signal,
                "type": "TECHNICAL_ANALYSIS",
                "current_price": round(price, 2),
                "ema_20": round(ema_20, 2),
                "ema_50": round(ema_50, 2),
                "ema_200": round(ema_200, 2),
                "rsi": round(rsi, 2),
                "rsi_status": "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral",
                "macd": round(macd, 4),
                "macd_signal": round(macd_signal, 4),
                "entry_price": round(entry_price, 2),
                "target": round(target, 2),
                "stop_loss": round(stop_loss, 2),
                "atr": round(atr, 2) if atr else None,
                "levels_method": levels_method,
                # F-12: honest label. "confidence" kept as an alias for backward
                # compatibility but explicitly documented as signal agreement.
                "signal_agreement_pct": signal_agreement_pct,
                "confidence": signal_agreement_pct,
                "confidence_basis": "signal_agreement",
                "timestamp": datetime.utcnow().isoformat(),
                "signals_used": [ema_signal, rsi_signal, macd_signal_result]
            }
            
            logger.info(
                f"Generated signal for {symbol}: {final_signal}",
                extra={
                    "symbol": symbol,
                    "signal": final_signal,
                    "confidence": signal["confidence"]
                }
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}", exc_info=True)
            return {
                "symbol": symbol,
                "signal": "HOLD",
                "type": "ERROR",
                "confidence": 0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    @staticmethod
    def _analyze_ema(price: float, ema_20: float, ema_50: float, ema_200: float) -> str:
        """Analyze EMA crossover signals"""
        try:
            # EMA 20 > EMA 50 > EMA 200 = Uptrend (BUY)
            if ema_20 > ema_50 > ema_200:
                return 'BUY'
            # EMA 20 < EMA 50 < EMA 200 = Downtrend (SELL)
            elif ema_20 < ema_50 < ema_200:
                return 'SELL'
            # Price above all EMAs (BUY)
            elif price > ema_20 > ema_50:
                return 'BUY'
            # Price below all EMAs (SELL)
            elif price < ema_20 < ema_50:
                return 'SELL'
            else:
                return 'HOLD'
        except Exception as e:
            logger.warning(f"EMA analysis error: {e}")
            return 'HOLD'

    @staticmethod
    def _analyze_rsi(rsi: float) -> str:
        """Analyze RSI signals"""
        try:
            if rsi > 70:
                return 'SELL'  # Overbought
            elif rsi < 30:
                return 'BUY'  # Oversold
            else:
                return 'HOLD'
        except Exception as e:
            logger.warning(f"RSI analysis error: {e}")
            return 'HOLD'

    @staticmethod
    def _analyze_macd(macd: float, macd_signal: float) -> str:
        """Analyze MACD signals"""
        try:
            if macd > macd_signal:
                return 'BUY'  # MACD above signal line
            elif macd < macd_signal:
                return 'SELL'  # MACD below signal line
            else:
                return 'HOLD'
        except Exception as e:
            logger.warning(f"MACD analysis error: {e}")
            return 'HOLD'
