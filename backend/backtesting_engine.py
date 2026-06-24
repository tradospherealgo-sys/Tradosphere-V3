"""
Backtesting Engine - Historical strategy performance analysis
Paper-trading focused with real historical data from market_data.py
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from technical_engine import TechnicalEngine
from signals_engine import SignalsEngine


class BaseStrategy:
    """Base class for all backtesting strategies"""

    def __init__(self):
        self.name = "Base Strategy"
        self.description = "Base strategy template"

    def generate_signal(self, candles: List[Dict]) -> Dict:
        """Generate signal from candles - must be overridden"""
        raise NotImplementedError


class TechnicalStrategy(BaseStrategy):
    """Technical analysis-based strategy using RSI and EMA crossovers"""

    def __init__(self):
        super().__init__()
        self.name = "Technical Strategy"
        self.description = "Uses RSI oversold < 30 for buy and EMA crossover for signals"

    def generate_signal(self, candles: List[Dict]) -> Dict:
        """Generate signal using technical indicators"""
        if not candles or len(candles) < 26:
            return {
                "status": "no_signal",
                "reason": "Insufficient candle data"
            }

        try:
            # Analyze with technical engine
            analysis = TechnicalEngine.analyze(candles)

            if analysis.get("status") != "success":
                return {"status": "no_signal", "reason": "Analysis failed"}

            # Extract indicators
            rsi = analysis.get("indicators", {}).get("rsi", 50)
            trend = analysis.get("trend", "NEUTRAL")
            ema_signal = analysis.get("ema_crossover_signal", "NONE")

            # Generate signal based on RSI and EMA
            signal = {
                "status": "no_signal",
                "reason": "No clear setup"
            }

            # RSI < 30 = oversold = potential buy
            if rsi < 30 and trend == "BULLISH" and ema_signal == "BUY":
                signal = {
                    "status": "success",
                    "direction": "BUY",
                    "confidence": int(min(85, 50 + (30 - rsi))),
                    "setup": "RSI Oversold + EMA Bullish",
                    "rsi": rsi,
                    "trend": trend
                }
            # RSI > 70 = overbought = potential sell
            elif rsi > 70 and trend == "BEARISH" and ema_signal == "SELL":
                signal = {
                    "status": "success",
                    "direction": "SELL",
                    "confidence": int(min(85, 50 + (rsi - 70))),
                    "setup": "RSI Overbought + EMA Bearish",
                    "rsi": rsi,
                    "trend": trend
                }

            return signal

        except Exception as e:
            return {
                "status": "error",
                "reason": str(e)
            }


class MomentumStrategy(BaseStrategy):
    """Momentum-based strategy using RSI"""

    def __init__(self):
        super().__init__()
        self.name = "Momentum Strategy"
        self.description = "Pure RSI-based momentum - oversold < 30 for buy, overbought > 70 for sell"

    def generate_signal(self, candles: List[Dict]) -> Dict:
        """Generate signal using RSI momentum"""
        if not candles or len(candles) < 14:
            return {
                "status": "no_signal",
                "reason": "Insufficient candle data"
            }

        try:
            # Calculate RSI manually
            rsi = self._calculate_rsi(candles, period=14)

            if rsi is None:
                return {"status": "no_signal", "reason": "Cannot calculate RSI"}

            # Simple momentum: Buy oversold, Sell overbought
            if rsi < 30:
                return {
                    "status": "success",
                    "direction": "BUY",
                    "confidence": int(80 - rsi / 2),  # Higher confidence when more oversold
                    "setup": "RSI Oversold",
                    "rsi": rsi
                }
            elif rsi > 70:
                return {
                    "status": "success",
                    "direction": "SELL",
                    "confidence": int(80 - (100 - rsi) / 2),  # Higher confidence when more overbought
                    "setup": "RSI Overbought",
                    "rsi": rsi
                }
            else:
                return {
                    "status": "no_signal",
                    "reason": f"RSI neutral at {rsi:.1f}",
                    "rsi": rsi
                }

        except Exception as e:
            return {
                "status": "error",
                "reason": str(e)
            }

    @staticmethod
    def _calculate_rsi(candles: List[Dict], period: int = 14) -> Optional[float]:
        """Calculate RSI from candles"""
        if len(candles) < period + 1:
            return None

        closes = [float(c.get("close", 0)) for c in candles[-period - 1:]]
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

        seed = sum([d for d in deltas[:period] if d > 0]) / period
        down_seed = sum([abs(d) for d in deltas[:period] if d < 0]) / period

        rs = seed / down_seed if down_seed != 0 else 100
        rsi = 100 - (100 / (1 + rs))

        for d in deltas[period:]:
            seed = (seed * (period - 1) + (d if d > 0 else 0)) / period
            down_seed = (down_seed * (period - 1) + (abs(d) if d < 0 else 0)) / period
            rs = seed / down_seed if down_seed != 0 else 100
            rsi = 100 - (100 / (1 + rs))

        return rsi


class Backtest:
    """Backtesting engine - run strategies on historical data"""

    PAPER_CAPITAL = 100000
    COMMISSION = 0.001  # 0.1% per trade

    @classmethod
    def run(
        cls,
        symbol: str,
        strategy: BaseStrategy,
        interval: str = "15",
        days_back: int = 30,
        initial_capital: float = 100000,
        market_data=None  # Inject for testing
    ) -> Dict:
        """Run backtest on historical data"""
        try:
            # Import here to avoid circular imports
            from market_data import AngelOneMarketData

            if market_data is None:
                # Try to get live data if available
                market_data = AngelOneMarketData(
                    api_key="",
                    client_code="",
                    pin="",
                    totp_secret=""
                )

            # Get historical candles
            candles = market_data.get_historical_candles(
                symbol, interval, limit=min(500, days_back * 24)  # Approximate candles
            )

            if not candles:
                return {
                    "status": "error",
                    "message": f"Cannot fetch candles for {symbol}"
                }

            # Simulate trading
            trades = []
            portfolio_value = initial_capital
            position = None

            for candle in candles:
                signal = strategy.generate_signal(candles[: candles.index(candle) + 1])

                # Entry
                if signal.get("status") == "success" and position is None:
                    entry_price = float(candle.get("close", 0))
                    position = {
                        "direction": signal.get("direction"),
                        "entry_price": entry_price,
                        "entry_time": candle.get("time"),
                        "quantity": int(portfolio_value / entry_price)
                    }

                # Exit (simple: opposite signal or after 5 candles)
                elif position and (
                    signal.get("direction") != position["direction"]
                    or len(candles) > candles.index(candle) + 5
                ):
                    exit_price = float(candle.get("close", 0))
                    pnl_percent = (
                        ((exit_price - position["entry_price"]) / position["entry_price"] * 100)
                        if position["direction"] == "BUY"
                        else ((position["entry_price"] - exit_price) / position["entry_price"] * 100)
                    )
                    pnl = portfolio_value * (pnl_percent / 100)
                    portfolio_value += pnl * (1 - cls.COMMISSION)

                    trades.append({
                        "entry_price": position["entry_price"],
                        "exit_price": exit_price,
                        "direction": position["direction"],
                        "pnl": pnl,
                        "pnl_percent": pnl_percent
                    })

                    position = None

            # Calculate statistics
            winning_trades = [t for t in trades if t["pnl"] > 0]
            total_return = ((portfolio_value - initial_capital) / initial_capital) * 100

            return {
                "status": "success",
                "symbol": symbol,
                "strategy": strategy.name,
                "period_days": days_back,
                "total_trades": len(trades),
                "winning_trades": len(winning_trades),
                "losing_trades": len(trades) - len(winning_trades),
                "win_rate": (len(winning_trades) / len(trades) * 100) if trades else 0,
                "initial_capital": initial_capital,
                "final_capital": round(portfolio_value, 2),
                "total_return_percent": round(total_return, 2),
                "max_drawdown": cls._calculate_max_drawdown(trades),
                "profit_factor": cls._calculate_profit_factor(trades),
                "trades": trades[:10]  # Return first 10 trades
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    @classmethod
    def compare_strategies(
        cls,
        symbol: str,
        interval: str = "15",
        days_back: int = 30,
        initial_capital: float = 100000
    ) -> Dict:
        """Compare all available strategies"""
        strategies = [
            TechnicalStrategy(),
            MomentumStrategy()
        ]

        results = []
        for strategy in strategies:
            result = cls.run(
                symbol=symbol,
                strategy=strategy,
                interval=interval,
                days_back=days_back,
                initial_capital=initial_capital
            )
            if result.get("status") == "success":
                results.append(result)

        # Sort by total return
        results.sort(key=lambda x: x.get("total_return_percent", 0), reverse=True)

        return {
            "symbol": symbol,
            "period_days": days_back,
            "strategies": results,
            "best_performer": results[0]["strategy"] if results else None
        }

    @staticmethod
    def _calculate_max_drawdown(trades: List[Dict]) -> float:
        """Calculate maximum drawdown percentage"""
        if not trades:
            return 0

        running_pnl = 0
        peak = 0
        max_dd = 0

        for trade in trades:
            running_pnl += trade.get("pnl", 0)
            if running_pnl > peak:
                peak = running_pnl
            drawdown = peak - running_pnl
            if drawdown > max_dd:
                max_dd = drawdown

        return max_dd

    @staticmethod
    def _calculate_profit_factor(trades: List[Dict]) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        gross_profit = sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) > 0)
        gross_loss = abs(sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) < 0))

        if gross_loss == 0:
            return gross_profit if gross_profit > 0 else 0

        return gross_profit / gross_loss
