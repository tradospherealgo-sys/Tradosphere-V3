"""
Post-Market Reconciliation & Logging System
Executes daily at 3:45 PM IST (post-market close)
Validates AI signals against actual market candles
Updates signal status to True Positive or False Positive
"""

import pytz
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from database import (
    SessionLocal, Signal, get_candles, get_metrics
)


class ReconciliationEngine:
    """Post-market reconciliation and signal validation"""

    # IST timezone
    IST = pytz.timezone('Asia/Kolkata')

    # Market close time
    MARKET_CLOSE_TIME = time(15, 45)  # 3:45 PM IST

    @staticmethod
    def is_reconciliation_time() -> bool:
        """Check if current time is within reconciliation window (3:45 PM - 4:00 PM IST)"""
        now = datetime.now(ReconciliationEngine.IST).time()
        # Allow 15-minute reconciliation window after market close
        start = time(15, 45)
        end = time(16, 0)
        return start <= now <= end


    @staticmethod
    def check_if_target_hit(candles: List[Dict], entry: float, target: float,
                           is_buy: bool = True) -> Tuple[bool, Optional[float], Optional[int]]:
        """
        Check if target was hit in candle data

        Returns:
            (target_hit: bool, hit_price: float, candle_index: int)
        """
        try:
            for idx, candle in enumerate(candles):
                high = candle.get('high', 0)
                low = candle.get('low', 0)

                if is_buy:
                    # For BUY: target is above entry, check if high >= target
                    if high >= target:
                        return True, high, idx
                else:
                    # For SELL: target is below entry, check if low <= target
                    if low <= target:
                        return True, low, idx

            return False, None, None
        except Exception as e:
            print(f"❌ Error checking target: {e}")
            return False, None, None


    @staticmethod
    def check_if_sl_hit(candles: List[Dict], entry: float, stop_loss: float,
                       is_buy: bool = True) -> Tuple[bool, Optional[float], Optional[int]]:
        """
        Check if stop loss was hit in candle data

        Returns:
            (sl_hit: bool, hit_price: float, candle_index: int)
        """
        try:
            for idx, candle in enumerate(candles):
                high = candle.get('high', 0)
                low = candle.get('low', 0)

                if is_buy:
                    # For BUY: SL is below entry, check if low <= SL
                    if low <= stop_loss:
                        return True, low, idx
                else:
                    # For SELL: SL is above entry, check if high >= SL
                    if high >= stop_loss:
                        return True, high, idx

            return False, None, None
        except Exception as e:
            print(f"❌ Error checking SL: {e}")
            return False, None, None


    @staticmethod
    def which_hit_first(target_info: Tuple[bool, Optional[float], Optional[int]],
                       sl_info: Tuple[bool, Optional[float], Optional[int]]) -> str:
        """
        Determine which was hit first: target or stop loss

        Returns:
            "TARGET" | "SL" | "NEITHER"
        """
        target_hit, _, target_idx = target_info
        sl_hit, _, sl_idx = sl_info

        if not target_hit and not sl_hit:
            return "NEITHER"
        elif not target_hit:
            return "SL"
        elif not sl_hit:
            return "TARGET"
        else:
            # Both hit, check which came first
            return "TARGET" if target_idx < sl_idx else "SL"


    @classmethod
    def reconcile_signal(cls, signal: Signal) -> Dict:
        """
        Reconcile a single signal against actual market data

        Args:
            signal: Signal ORM object

        Returns:
            Dict with reconciliation results
        """
        try:
            symbol = signal.symbol
            direction = signal.verdict
            entry = signal.entry
            target = signal.target
            sl = signal.sl
            confidence = signal.confidence
            signal_id = signal.id

            # Fetch candles for the day post-signal generation
            candles = get_candles(symbol, interval="15", limit=100)

            if not candles or len(candles) < 5:
                return {
                    "signal_id": signal_id,
                    "symbol": symbol,
                    "status": "INCONCLUSIVE",
                    "reason": "Insufficient candle data",
                    "reconciled_at": datetime.utcnow().isoformat()
                }

            is_buy = (direction.upper() == "BUY")

            # Check if target was hit
            target_hit_info = cls.check_if_target_hit(candles, entry, target, is_buy)
            target_hit, target_price, target_candle = target_hit_info

            # Check if SL was hit
            sl_hit_info = cls.check_if_sl_hit(candles, entry, sl, is_buy)
            sl_hit, sl_price, sl_candle = sl_hit_info

            # Determine outcome
            outcome = cls.which_hit_first(target_hit_info, sl_hit_info)

            # Map outcome to True Positive / False Positive
            if outcome == "TARGET":
                status = "TRUE_POSITIVE"
                result_description = f"✅ Target HIT at {target_price:.2f}"
                pnl = abs(target_price - entry) if is_buy else abs(entry - target_price)
            elif outcome == "SL":
                status = "FALSE_POSITIVE"
                result_description = f"❌ Stop Loss HIT at {sl_price:.2f}"
                pnl = -(abs(sl_price - entry) if is_buy else abs(entry - sl_price))
            else:
                status = "INCONCLUSIVE"
                result_description = "⚠️ Neither target nor SL hit during session"
                pnl = 0.0

            return {
                "signal_id": signal_id,
                "symbol": symbol,
                "direction": direction,
                "entry": entry,
                "target": target,
                "stop_loss": sl,
                "confidence": confidence,
                "status": status,
                "outcome": outcome,
                "result": result_description,
                "pnl": round(pnl, 2),
                "target_hit": target_hit,
                "sl_hit": sl_hit,
                "reconciled_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"❌ Error reconciling signal {signal.id}: {e}")
            return {
                "signal_id": signal.id,
                "status": "ERROR",
                "reason": str(e),
                "reconciled_at": datetime.utcnow().isoformat()
            }


    @classmethod
    def reconcile_all_pending(cls) -> Dict:
        """
        Reconcile all pending signals for the current day

        Returns:
            Dict with reconciliation summary
        """
        try:
            db = SessionLocal()

            # Get all PENDING signals from today
            from datetime import date
            today = datetime.utcnow().date()

            pending_signals = db.query(Signal).filter(
                Signal.status == "PENDING",
                Signal.timestamp >= datetime.combine(today, datetime.min.time())
            ).all()

            print(f"\n📊 RECONCILING {len(pending_signals)} pending signals...")

            results = []
            true_positives = 0
            false_positives = 0
            inconclusive = 0

            for signal in pending_signals:
                reconciliation = cls.reconcile_signal(signal)
                results.append(reconciliation)

                status = reconciliation.get("status")

                # Update signal status in database
                if status in ["TRUE_POSITIVE", "FALSE_POSITIVE", "INCONCLUSIVE"]:
                    signal.status = status
                    db.commit()

                    if status == "TRUE_POSITIVE":
                        true_positives += 1
                    elif status == "FALSE_POSITIVE":
                        false_positives += 1
                    else:
                        inconclusive += 1

                print(f"   {signal.symbol}: {status} - {reconciliation.get('result')}")

            # Calculate accuracy
            total_resolved = true_positives + false_positives
            accuracy = (true_positives / total_resolved * 100) if total_resolved > 0 else 0

            db.close()

            return {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "signals_reconciled": len(pending_signals),
                "true_positives": true_positives,
                "false_positives": false_positives,
                "inconclusive": inconclusive,
                "accuracy_rate": round(accuracy, 2),
                "results": results
            }

        except Exception as e:
            print(f"❌ Error in reconciliation batch: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


    @staticmethod
    def generate_reconciliation_insights() -> Dict:
        """
        Generate learning insights from reconciliation data

        Returns:
            Dict with accuracy trends and recommendations
        """
        try:
            db = SessionLocal()

            # Query all non-pending signals
            resolved_signals = db.query(Signal).filter(
                Signal.status.in_(["TRUE_POSITIVE", "FALSE_POSITIVE"])
            ).all()

            db.close()

            if not resolved_signals:
                return {
                    "status": "insufficient_data",
                    "message": "No resolved signals yet"
                }

            total = len(resolved_signals)
            tp = len([s for s in resolved_signals if s.status == "TRUE_POSITIVE"])
            fp = len([s for s in resolved_signals if s.status == "FALSE_POSITIVE"])

            win_rate = (tp / total * 100) if total > 0 else 0

            # Analyze by symbol
            nifty_signals = [s for s in resolved_signals if s.symbol == "NIFTY"]
            bnf_signals = [s for s in resolved_signals if s.symbol == "BANKNIFTY"]

            nifty_tp = len([s for s in nifty_signals if s.status == "TRUE_POSITIVE"])
            bnf_tp = len([s for s in bnf_signals if s.status == "TRUE_POSITIVE"])

            nifty_rate = (nifty_tp / len(nifty_signals) * 100) if nifty_signals else 0
            bnf_rate = (bnf_tp / len(bnf_signals) * 100) if bnf_signals else 0

            insights = []

            if win_rate >= 60:
                insights.append({
                    "type": "positive",
                    "title": "Strong Signal Accuracy",
                    "message": f"✅ Signal accuracy is {win_rate:.1f}% - Keep current setup parameters"
                })
            elif win_rate >= 50:
                insights.append({
                    "type": "info",
                    "title": "Moderate Accuracy",
                    "message": f"⚠️ Signal accuracy is {win_rate:.1f}% - Monitor for improvements"
                })
            else:
                insights.append({
                    "type": "warning",
                    "title": "Low Signal Accuracy",
                    "message": f"❌ Signal accuracy is {win_rate:.1f}% - Consider adjusting parameters"
                })

            if nifty_rate > bnf_rate:
                insights.append({
                    "type": "info",
                    "title": "NIFTY Outperforming",
                    "message": f"📈 NIFTY: {nifty_rate:.1f}% vs BANKNIFTY: {bnf_rate:.1f}%"
                })
            elif bnf_rate > nifty_rate:
                insights.append({
                    "type": "info",
                    "title": "BANKNIFTY Outperforming",
                    "message": f"📊 BANKNIFTY: {bnf_rate:.1f}% vs NIFTY: {nifty_rate:.1f}%"
                })

            return {
                "status": "success",
                "total_signals": total,
                "true_positives": tp,
                "false_positives": fp,
                "overall_accuracy": round(win_rate, 2),
                "nifty_accuracy": round(nifty_rate, 2),
                "banknifty_accuracy": round(bnf_rate, 2),
                "insights": insights,
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"❌ Error generating insights: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


if __name__ == "__main__":
    # Test reconciliation
    print("\n" + "="*70)
    print("📊 POST-MARKET RECONCILIATION ENGINE - TEST")
    print("="*70)

    # Check if it's time to reconcile
    if ReconciliationEngine.is_reconciliation_time():
        print("✅ Current time is within reconciliation window (3:45 PM - 4:00 PM IST)")
        result = ReconciliationEngine.reconcile_all_pending()
        print(f"\n✅ Reconciliation Complete:")
        print(f"   True Positives: {result.get('true_positives', 0)}")
        print(f"   False Positives: {result.get('false_positives', 0)}")
        print(f"   Accuracy Rate: {result.get('accuracy_rate', 0)}%")
    else:
        print("⏰ Not within reconciliation window")
        print("   Reconciliation runs at 3:45 PM IST (post-market close)")

    # Generate insights
    insights = ReconciliationEngine.generate_reconciliation_insights()
    print(f"\n📈 Reconciliation Insights:")
    print(f"   Overall Accuracy: {insights.get('overall_accuracy', '--')}%")
    print(f"   NIFTY: {insights.get('nifty_accuracy', '--')}%")
    print(f"   BANKNIFTY: {insights.get('banknifty_accuracy', '--')}%")

    print("\n" + "="*70)
