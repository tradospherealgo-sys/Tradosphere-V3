"""
Learning System - Tracks signal performance and learns from results
Updates performance metrics based on signal outcomes
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from database import get_db, Signal, Trade


class LearningEngine:
    """
    Learning engine for tracking signal performance
    Analyzes win rates, profit factors, and generates insights
    """

    @staticmethod
    def calculate_signal_performance(symbol: str = None, days: int = 30) -> Dict:
        """
        Calculate performance metrics for signals

        Args:
            symbol: Optional symbol filter (NIFTY, BANKNIFTY)
            days: Number of days to analyze

        Returns:
            Dict with performance metrics
        """
        try:
            db = get_db()
            try:
                # Get signals in timeframe
                query = db.query(Signal)
                if symbol:
                    query = query.filter(Signal.symbol == symbol)

                cutoff_date = datetime.utcnow() - timedelta(days=days)
                signals = query.filter(Signal.timestamp >= cutoff_date).all()

                if not signals:
                    return {
                        "status": "no_data",
                        "message": f"No signals found for {symbol or 'all'} in last {days} days"
                    }

                # Get associated trades
                signal_ids = [s.id for s in signals]
                trades = db.query(Trade).filter(Trade.signal_id.in_(signal_ids)).all()

                # Calculate metrics
                total_signals = len(signals)
                total_trades = len(trades)

                # Profitable trades
                winning_trades = [t for t in trades if t.pnl and t.pnl > 0]
                losing_trades = [t for t in trades if t.pnl and t.pnl < 0]

                win_count = len(winning_trades)
                loss_count = len(losing_trades)
                win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

                # P&L analysis
                total_pnl = sum(t.pnl for t in trades if t.pnl)
                avg_win = sum(t.pnl for t in winning_trades) / win_count if winning_trades else 0
                avg_loss = abs(sum(t.pnl for t in losing_trades) / loss_count) if losing_trades else 0
                profit_factor = avg_win / avg_loss if avg_loss > 0 else 0

                # Breakdown by setup type
                breakout_signals = [s for s in signals if s.verdict and "BREAKOUT" in s.verdict.upper()]
                breakout_trades = [t for t in trades if t.signal_id in [s.id for s in breakout_signals] and t.pnl]
                breakout_win_rate = (len([t for t in breakout_trades if t.pnl > 0]) / len(breakout_trades) * 100) if breakout_trades else 0

                return {
                    "status": "success",
                    "symbol": symbol or "all",
                    "period_days": days,
                    "total_signals": total_signals,
                    "total_trades": total_trades,
                    "wins": win_count,
                    "losses": loss_count,
                    "win_rate": round(win_rate, 2),
                    "total_pnl": round(total_pnl, 2),
                    "avg_win": round(avg_win, 2),
                    "avg_loss": round(avg_loss, 2),
                    "profit_factor": round(profit_factor, 2),
                    "breakout_signals": len(breakout_signals),
                    "breakout_win_rate": round(breakout_win_rate, 2),
                    "timestamp": datetime.utcnow().isoformat()
                }

            finally:
                db.close()

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    @staticmethod
    def get_setup_analysis() -> Dict:
        """
        Analyze performance by setup type

        Returns:
            Dict with setup-wise performance
        """
        try:
            db = get_db()
            try:
                # Get all signals from last 60 days
                cutoff_date = datetime.utcnow() - timedelta(days=60)
                signals = db.query(Signal).filter(Signal.timestamp >= cutoff_date).all()

                setups = {}

                for signal in signals:
                    setup_type = signal.verdict or "UNKNOWN"

                    if setup_type not in setups:
                        setups[setup_type] = {
                            "count": 0,
                            "wins": 0,
                            "losses": 0,
                            "pnl": 0
                        }

                    setups[setup_type]["count"] += 1

                    # Get associated trades
                    trades = db.query(Trade).filter(Trade.signal_id == signal.id).all()
                    for trade in trades:
                        if trade.pnl:
                            if trade.pnl > 0:
                                setups[setup_type]["wins"] += 1
                            else:
                                setups[setup_type]["losses"] += 1
                            setups[setup_type]["pnl"] += trade.pnl

                # Calculate win rates
                for setup_type in setups:
                    setup = setups[setup_type]
                    total = setup["wins"] + setup["losses"]
                    setup["win_rate"] = (setup["wins"] / total * 100) if total > 0 else 0
                    setup["avg_pnl"] = setup["pnl"] / setup["count"] if setup["count"] > 0 else 0

                return {
                    "status": "success",
                    "setups": setups,
                    "period_days": 60,
                    "timestamp": datetime.utcnow().isoformat()
                }

            finally:
                db.close()

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    @staticmethod
    def get_learning_insights() -> Dict:
        """
        Generate learning insights from signal history

        Returns:
            Dict with actionable insights and recommendations
        """
        try:
            # Get performance metrics
            perf = LearningEngine.calculate_signal_performance(days=60)
            setup_analysis = LearningEngine.get_setup_analysis()

            insights = []
            recommendations = []

            if perf.get("status") == "success":
                win_rate = perf.get("win_rate", 0)
                profit_factor = perf.get("profit_factor", 0)

                # Win rate analysis
                if win_rate >= 60:
                    insights.append("✓ Strong win rate indicates good signal quality")
                    recommendations.append("Increase position size for confirmed signals")
                elif win_rate >= 50:
                    insights.append("✓ Win rate is at break-even - focus on risk management")
                    recommendations.append("Maintain strict stop losses")
                else:
                    insights.append("⚠ Win rate is below 50% - signals need refinement")
                    recommendations.append("Review signal generation logic")

                # Profit factor analysis
                if profit_factor > 1.5:
                    insights.append("✓ Excellent profit factor - average winners are 1.5x larger than losers")
                elif profit_factor > 1.0:
                    insights.append("✓ Positive profit factor indicates profitable trading")
                else:
                    insights.append("⚠ Losses are larger than wins - improve entry precision")
                    recommendations.append("Use tighter entry criteria")

                # Setup analysis
                if setup_analysis.get("status") == "success":
                    setups = setup_analysis.get("setups", {})
                    best_setup = max(setups.items(), key=lambda x: x[1].get("win_rate", 0), default=(None, {}))
                    worst_setup = min(setups.items(), key=lambda x: x[1].get("win_rate", 100), default=(None, {}))

                    if best_setup[0]:
                        insights.append(f"✓ {best_setup[0]} has highest win rate ({best_setup[1].get('win_rate', 0):.1f}%)")
                        recommendations.append(f"Focus more on {best_setup[0]} setups")

                    if worst_setup[0] and worst_setup[1].get("win_rate", 0) < 40:
                        insights.append(f"⚠ {worst_setup[0]} has low win rate - consider avoiding")
                        recommendations.append(f"Avoid {worst_setup[0]} setups or improve criteria")

            return {
                "status": "success",
                "insights": insights,
                "recommendations": recommendations,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    @staticmethod
    def get_monthly_performance() -> Dict:
        """
        Get performance breakdown by month

        Returns:
            Dict with monthly win rates and P&L
        """
        try:
            db = get_db()
            try:
                # Get signals from last 6 months
                cutoff_date = datetime.utcnow() - timedelta(days=180)
                signals = db.query(Signal).filter(Signal.timestamp >= cutoff_date).all()

                months = {}

                for signal in signals:
                    month_key = signal.timestamp.strftime("%Y-%m") if signal.timestamp else "unknown"

                    if month_key not in months:
                        months[month_key] = {
                            "signals": 0,
                            "trades": 0,
                            "wins": 0,
                            "losses": 0,
                            "pnl": 0
                        }

                    months[month_key]["signals"] += 1

                    # Get trades
                    trades = db.query(Trade).filter(Trade.signal_id == signal.id).all()
                    for trade in trades:
                        months[month_key]["trades"] += 1
                        if trade.pnl:
                            if trade.pnl > 0:
                                months[month_key]["wins"] += 1
                            else:
                                months[month_key]["losses"] += 1
                            months[month_key]["pnl"] += trade.pnl

                # Calculate metrics
                for month_key in months:
                    month = months[month_key]
                    total_trades = month["wins"] + month["losses"]
                    month["win_rate"] = (month["wins"] / total_trades * 100) if total_trades > 0 else 0
                    month["pnl"] = round(month["pnl"], 2)

                return {
                    "status": "success",
                    "months": dict(sorted(months.items())),
                    "timestamp": datetime.utcnow().isoformat()
                }

            finally:
                db.close()

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
