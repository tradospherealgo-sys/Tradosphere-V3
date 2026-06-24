"""
Signal Intelligence Engine - Professional trading signal generation
Integrates technical, options, and AI analysis for comprehensive market signals
"""

from datetime import datetime
from typing import Dict, Optional, List

from market_data import AngelOneMarketData
from database import save_signal, get_metrics, get_candles, get_latest_option_chain
from technical_engine import TechnicalEngine
from options_engine import OptionsEngine
from ai_engine import AIEngine


class SignalQualityScore:
    """Calculate professional signal quality score"""

    @staticmethod
    def calculate_technical_score(technical_data: Dict) -> tuple:
        """
        Calculate technical score (0-40 points)

        Returns: (score, max_score)
        """
        score = 0
        max_score = 40

        try:
            if not technical_data or technical_data.get("status") != "success":
                return 0, max_score

            trend = technical_data.get("trend", "NEUTRAL")
            momentum = technical_data.get("momentum", "NEUTRAL")
            setup = technical_data.get("setup", "RANGE_BOUND")
            rsi = technical_data.get("indicators", {}).get("rsi", 50)
            price_vs_vwap = technical_data.get("price_vs_indicators", {}).get("price_vs_vwap", "neutral")

            # Trend score (10 points)
            if trend in ["BULLISH", "BEARISH"]:
                score += 10
            elif trend == "NEUTRAL":
                score += 5

            # Momentum score (10 points)
            if "STRONG" in momentum:
                score += 10
            elif momentum != "NEUTRAL":
                score += 7
            elif rsi and (30 < rsi < 70):
                score += 5

            # Setup score (10 points)
            if "BREAKOUT" in setup:
                score += 10
            elif "STRONG" in setup:
                score += 8
            elif setup != "RANGE_BOUND":
                score += 6

            # VWAP score (10 points)
            if price_vs_vwap in ["above", "below"]:
                score += 10

            return min(score, max_score), max_score

        except:
            return 0, max_score

    @staticmethod
    def calculate_options_score(options_data: Dict) -> tuple:
        """
        Calculate options score (0-40 points)

        Returns: (score, max_score)
        """
        score = 0
        max_score = 40

        try:
            if not options_data or options_data.get("status") != "success":
                return 0, max_score

            bias = options_data.get("bias", "NEUTRAL")
            pcr = options_data.get("pcr", 1.0)
            oi_skew = options_data.get("oi_skew", "BALANCED")

            # PCR score (15 points)
            if pcr > 1.2:
                score += 15
            elif pcr > 1.0:
                score += 12
            elif pcr < 0.8:
                score += 10
            elif pcr < 1.0:
                score += 8
            else:
                score += 5

            # OI Skew score (15 points)
            if oi_skew != "BALANCED":
                score += 15
            else:
                score += 8

            # Bias confirmation score (10 points)
            if bias in ["BULLISH", "BEARISH"]:
                score += 10
            elif bias == "NEUTRAL":
                score += 5

            return min(score, max_score), max_score

        except:
            return 0, max_score

    @staticmethod
    def calculate_market_score(technical_data: Dict, options_data: Dict) -> tuple:
        """
        Calculate market condition score (0-20 points)

        Returns: (score, max_score)
        """
        score = 0
        max_score = 20

        try:
            # Trend strength (10 points)
            trend = technical_data.get("trend", "NEUTRAL") if technical_data else "NEUTRAL"
            momentum = technical_data.get("momentum", "NEUTRAL") if technical_data else "NEUTRAL"

            if trend in ["BULLISH", "BEARISH"] and "STRONG" in momentum:
                score += 10
            elif trend in ["BULLISH", "BEARISH"]:
                score += 7
            else:
                score += 3

            # Volatility/Setup alignment (10 points)
            setup = technical_data.get("setup", "RANGE_BOUND") if technical_data else "RANGE_BOUND"
            oi_skew = options_data.get("oi_skew", "BALANCED") if options_data else "BALANCED"

            if setup != "RANGE_BOUND" and oi_skew != "BALANCED":
                score += 10
            elif setup != "RANGE_BOUND" or oi_skew != "BALANCED":
                score += 7
            else:
                score += 3

            return min(score, max_score), max_score

        except:
            return 0, max_score


class SignalGenerator:
    """Generate professional trading signals with comprehensive analysis"""

    def __init__(self, market: AngelOneMarketData = None):
        """Initialize with optional market data instance"""
        self.market = market

    def _analyze_symbol(self, symbol: str, price: float) -> Optional[Dict]:
        """
        Analyze a symbol using comprehensive multi-engine analysis

        Args:
            symbol: NIFTY or BANKNIFTY
            price: Current price

        Returns:
            Dict with professional signal format
        """
        try:
            # Get technical analysis
            candles = get_candles(symbol, interval="15", limit=100)
            if not candles or len(candles) < 14:
                print(f"⚠️  Insufficient candle data for {symbol}, skipping signal")
                return None

            technical_data = TechnicalEngine.analyze(candles)

            # Get options analysis
            option_chain = get_latest_option_chain(symbol)
            if not option_chain:
                print(f"⚠️  No option chain data for {symbol}, skipping signal")
                return None

            # Fetch fresh option chain with all data
            if self.market:
                fresh_chain = self.market.get_option_chain(symbol)
                if fresh_chain and fresh_chain.get("status") == "success":
                    option_chain = fresh_chain

            options_data = OptionsEngine.analyze(option_chain)

            # Get AI analysis for market summary
            ai_summary = AIEngine.generate_market_summary(technical_data, options_data)

            # Generate comprehensive signal
            return self._generate_comprehensive_signal(
                symbol, price, technical_data, options_data, ai_summary
            )

        except Exception as e:
            print(f"❌ Error analyzing {symbol}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _generate_comprehensive_signal(self, symbol: str, price: float,
                                      technical_data: Dict, options_data: Dict,
                                      ai_summary: Dict) -> Optional[Dict]:
        """
        Generate comprehensive professional signal

        Args:
            symbol: NIFTY or BANKNIFTY
            price: Current price
            technical_data: Technical analysis
            options_data: Options analysis
            ai_summary: AI market summary

        Returns:
            Dict with professional signal format
        """
        try:
            # Calculate quality scores
            tech_score, tech_max = SignalQualityScore.calculate_technical_score(technical_data)
            opt_score, opt_max = SignalQualityScore.calculate_options_score(options_data)
            mkt_score, mkt_max = SignalQualityScore.calculate_market_score(technical_data, options_data)

            total_score = tech_score + opt_score + mkt_score
            total_max = tech_max + opt_max + mkt_max
            confidence = min((total_score / total_max * 100), 99) if total_max > 0 else 0

            # Extract data
            trend = technical_data.get("trend", "NEUTRAL")
            momentum = technical_data.get("momentum", "NEUTRAL")
            setup = technical_data.get("setup", "RANGE_BOUND")
            rsi = technical_data.get("indicators", {}).get("rsi", 50)
            ema20 = technical_data.get("indicators", {}).get("ema_20", price)
            vwap = technical_data.get("indicators", {}).get("vwap", price)

            pcr = options_data.get("pcr", 1.0)
            opt_bias = options_data.get("bias", "NEUTRAL")
            support = options_data.get("support", price - 100)
            resistance = options_data.get("resistance", price + 100)
            max_pain = options_data.get("max_pain", price)
            oi_skew = options_data.get("oi_skew", "BALANCED")

            # Determine market bias from AI
            market_bias = ai_summary.get("bias", "NEUTRAL") if ai_summary else trend

            # Determine direction based on all factors
            bullish_score = 0
            bearish_score = 0
            reasons = []

            # Technical signals
            if trend == "BULLISH":
                bullish_score += 2
                reasons.append("✓ Bullish trend confirmed")
            elif trend == "BEARISH":
                bearish_score += 2
                reasons.append("✓ Bearish trend confirmed")

            if "STRONG" in momentum:
                if "BULLISH" in momentum:
                    bullish_score += 2
                    reasons.append(f"✓ Strong bullish momentum (RSI {rsi:.0f})")
                else:
                    bearish_score += 2
                    reasons.append(f"✓ Strong bearish momentum (RSI {rsi:.0f})")

            if price > vwap:
                bullish_score += 1
                reasons.append("✓ Price above VWAP")
            else:
                bearish_score += 1
                reasons.append("✓ Price below VWAP")

            if "BREAKOUT" in setup:
                if "UPSIDE" in setup:
                    bullish_score += 2
                    reasons.append("✓ Upside breakout detected")
                elif "DOWNSIDE" in setup:
                    bearish_score += 2
                    reasons.append("✓ Downside breakout detected")

            # Options signals
            if pcr > 1.2:
                bullish_score += 2
                reasons.append(f"✓ High PCR {pcr:.2f} (put dominance)")
            elif pcr < 0.8:
                bearish_score += 2
                reasons.append(f"✓ Low PCR {pcr:.2f} (call dominance)")
            else:
                reasons.append(f"✓ Neutral PCR {pcr:.2f}")

            if "HEAVY" in oi_skew:
                if "PUT" in oi_skew:
                    bullish_score += 1
                    reasons.append("✓ OI skew bullish (put heavy)")
                elif "CALL" in oi_skew:
                    bearish_score += 1
                    reasons.append("✓ OI skew bearish (call heavy)")

            # Determine signal direction
            if bullish_score > bearish_score and confidence >= 50:
                direction = "BUY"
            elif bearish_score > bullish_score and confidence >= 50:
                direction = "SELL"
            else:
                direction = "WAIT"
                reasons = ["⚠️ Insufficient conviction for trade"]

            # Calculate entry, target, and SL
            if symbol == "NIFTY":
                atr_equiv = 200
                entry_offset = 50
            else:  # BANKNIFTY
                atr_equiv = 300
                entry_offset = 100

            if direction == "BUY":
                entry_zone_low = round(price - entry_offset, 0)
                entry_zone_high = round(price + entry_offset, 0)
                target = round(resistance if resistance > price else price + atr_equiv * 1.5, 0)
                sl = round(support if support < price else price - atr_equiv, 0)
                invalidation = round(support - 100, 0)

            elif direction == "SELL":
                entry_zone_low = round(price - entry_offset, 0)
                entry_zone_high = round(price + entry_offset, 0)
                target = round(support if support < price else price - atr_equiv * 1.5, 0)
                sl = round(resistance if resistance > price else price + atr_equiv, 0)
                invalidation = round(resistance + 100, 0)

            else:  # WAIT
                entry_zone_low = entry_zone_high = round(price, 0)
                target = sl = invalidation = 0

            # Determine risk level
            if direction != "WAIT":
                risk_amount = abs(sl - price)
                reward_amount = abs(target - price)
                risk_reward = reward_amount / risk_amount if risk_amount > 0 else 0

                if risk_reward >= 2.0:
                    risk_level = "LOW"
                elif risk_reward >= 1.0:
                    risk_level = "MEDIUM"
                else:
                    risk_level = "HIGH"
            else:
                risk_level = "N/A"

            # Build professional signal
            signal_dict = {
                "instrument": symbol,
                "market_bias": market_bias,
                "direction": direction,
                "setup": setup,
                "entry_zone": f"{entry_zone_low}-{entry_zone_high}",
                "entry": round((entry_zone_low + entry_zone_high) / 2, 0),
                "target": target,
                "stop_loss": sl,
                "invalidation": invalidation if direction != "WAIT" else None,
                "confidence": round(confidence, 1),
                "risk_level": risk_level,
                "reasons": reasons,
                "quality_score": {
                    "technical": f"{tech_score}/{tech_max}",
                    "options": f"{opt_score}/{opt_max}",
                    "market": f"{mkt_score}/{mkt_max}",
                    "overall": f"{total_score}/{total_max}"
                },
                "analysis": {
                    "trend": trend,
                    "momentum": momentum,
                    "rsi": round(rsi, 2),
                    "pcr": round(pcr, 3),
                    "oi_skew": oi_skew,
                    "support": round(support, 2),
                    "resistance": round(resistance, 2),
                    "max_pain": round(max_pain, 2)
                },
                "timestamp": datetime.utcnow().isoformat()
            }

            # Save to database
            if direction != "WAIT":
                db_signal = save_signal(
                    symbol=symbol,
                    entry=round((entry_zone_low + entry_zone_high) / 2, 0),
                    sl=sl,
                    target=target,
                    verdict=direction,
                    confidence=round(confidence, 1),
                    ema_signal=trend,
                    oi_bias=opt_bias,
                    pcr=round(pcr, 3)
                )
                signal_dict["id"] = db_signal.get("id")
                signal_dict["created_at"] = db_signal.get("timestamp")

            self._print_signal(signal_dict)
            return signal_dict

        except Exception as e:
            print(f"❌ Error generating signal: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _print_signal(self, signal: Dict):
        """Print formatted signal output"""
        print(f"\n{'='*70}")
        print(f"🎯 TRADOSPHERE SIGNAL")
        print(f"{'='*70}")
        print(f"Instrument: {signal['instrument']}")
        print(f"Market Bias: {signal['market_bias']} | Direction: {signal['direction']}")
        print(f"Setup: {signal['setup']}")
        print(f"Entry Zone: {signal['entry_zone']}")
        print(f"Target: {signal['target']} | Stop Loss: {signal['stop_loss']}")
        print(f"Confidence: {signal['confidence']}% | Risk Level: {signal['risk_level']}")
        print(f"Quality Score: {signal['quality_score']['overall']}")
        print(f"Reasons:")
        for reason in signal['reasons']:
            print(f"  {reason}")
        print(f"{'='*70}")

    def generate_signals(self) -> Dict:
        """Generate comprehensive signals for all symbols"""
        signals = []

        print("\n" + "="*70)
        print("🎯 SIGNAL INTELLIGENCE ENGINE")
        print("="*70)

        # Get current prices
        nifty_price = None
        banknifty_price = None

        if self.market:
            nifty_data = self.market.get_nifty_price()
            banknifty_data = self.market.get_banknifty_price()

            if nifty_data:
                nifty_price = nifty_data.get("ltp")
            if banknifty_data:
                banknifty_price = banknifty_data.get("ltp")

        # Generate NIFTY signal
        if nifty_price:
            nifty_signal = self._analyze_symbol("NIFTY", nifty_price)
            if nifty_signal:
                signals.append(nifty_signal)
        else:
            print("⚠️  NIFTY price not available")

        # Generate BANKNIFTY signal
        if banknifty_price:
            bnf_signal = self._analyze_symbol("BANKNIFTY", banknifty_price)
            if bnf_signal:
                signals.append(bnf_signal)
        else:
            print("⚠️  BANKNIFTY price not available")

        metrics = get_metrics()

        print("\n" + "="*70)
        return {
            "status": "success" if signals else "no_signals",
            "count": len(signals),
            "signals": signals,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics
        }


def generate_on_demand() -> Dict:
    """Generate signals on-demand using comprehensive real analysis"""
    try:
        from market_data import AngelOneMarketData

        print("\n🚀 Initializing market data...")
        market = AngelOneMarketData()

        generator = SignalGenerator(market)
        result = generator.generate_signals()
        return result
    except Exception as e:
        print(f"❌ Signal generation error: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
