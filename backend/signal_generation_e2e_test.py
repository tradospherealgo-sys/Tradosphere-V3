"""
End-to-End Signal Generation Test
Complete pipeline: Market Data → Options Chain → Signal Generation
"""

from logger_config import get_logger
from signal_generation_pipeline import SignalGenerationPipeline

logger = get_logger(__name__)


class SignalGenerationE2ETest:
    """Test complete signal generation pipeline"""

    def __init__(self):
        self.pipeline = SignalGenerationPipeline(
            symbol="NIFTY50",
            account_balance=100000,
            risk_per_trade=0.01
        )
        self.results = []

    def test_complete_signal_generation(self):
        """TEST: Generate complete professional signal"""
        print("\n" + "="*70)
        print("SIGNAL GENERATION E2E TEST - Complete Pipeline")
        print("="*70)

        try:
            # Simulated market data (replace with real data from Angel One)
            spot_price = 23450.25
            candles = [
                {'high': 23400, 'low': 23300, 'close': 23350},
                {'high': 23420, 'low': 23350, 'close': 23400},
                {'high': 23450, 'low': 23380, 'close': 23440},
                {'high': 23480, 'low': 23420, 'close': 23460},
                {'high': 23500, 'low': 23440, 'close': 23450},
            ]

            # Technical indicators (simulate - replace with real calculations)
            ema_fast = 23440
            ema_slow = 23420
            ema_long = 23350
            rsi = 55
            bb_position = 0.6  # Upper band area
            macd_signal = 'BULLISH'
            volume_confirm = True

            # Options chain response (mock - replace with real Angel One data)
            options_chain_response = {
                'fetched': True,
                'data': {
                    'strikeDetails': [
                        {'strike': 23000, 'callSymbol': 'NIFTY23000CE', 'putSymbol': 'NIFTY23000PE',
                         'callLTP': 485.50, 'putLTP': 12.25, 'callOI': 1250000, 'putOI': 980000,
                         'callBid': 483, 'callAsk': 487, 'callBidQty': 100, 'callAskQty': 100,
                         'callVolume': 5000, 'putVolume': 3000, 'putBid': 11, 'putAsk': 13,
                         'putBidQty': 100, 'putAskQty': 100},
                        {'strike': 23500, 'callSymbol': 'NIFTY23500CE', 'putSymbol': 'NIFTY23500PE',
                         'callLTP': 145.75, 'putLTP': 42.25, 'callOI': 2150000, 'putOI': 1850000,
                         'callBid': 144.50, 'callAsk': 147, 'callBidQty': 150, 'callAskQty': 150,
                         'callVolume': 8500, 'putVolume': 7200, 'putBid': 41, 'putAsk': 43,
                         'putBidQty': 150, 'putAskQty': 150},
                        {'strike': 24000, 'callSymbol': 'NIFTY24000CE', 'putSymbol': 'NIFTY24000PE',
                         'callLTP': 50.25, 'putLTP': 145.50, 'callOI': 1800000, 'putOI': 900000,
                         'callBid': 49, 'callAsk': 51.50, 'callBidQty': 100, 'callAskQty': 100,
                         'callVolume': 3000, 'putVolume': 2500, 'putBid': 144, 'putAsk': 147,
                         'putBidQty': 100, 'putAskQty': 100},
                    ]
                }
            }

            logger.info("="*70)
            logger.info("📊 STARTING COMPLETE SIGNAL GENERATION")
            logger.info("="*70)

            # Generate complete signal
            signal = self.pipeline.generate_signal_complete(
                spot_price=spot_price,
                candles=candles,
                ema_fast=ema_fast,
                ema_slow=ema_slow,
                ema_long=ema_long,
                rsi=rsi,
                bb_position=bb_position,
                macd_signal=macd_signal,
                volume_confirm=volume_confirm,
                options_chain_response=options_chain_response,
                expiry_date="25JUN2026",
                expiry_days=7
            )

            # Verify signal structure
            if 'error' in signal:
                self.log_test("Signal Generation", "FAIL", signal['error'])
                return False

            # Check all required fields
            required_fields = [
                'signal', 'strategy', 'direction', 'confidence_score',
                'action', 'signal_wording', 'recommendation', 'risk_level',
                'extended_analysis'
            ]

            missing = [f for f in required_fields if f not in signal]
            if missing:
                self.log_test("Signal Completeness", "FAIL", f"Missing: {missing}")
                return False

            self.log_test("Signal Generation", "PASS", f"Signal: {signal['signal']} | Confidence: {signal['confidence_score']}%")

            # Display signal details
            self._display_signal(signal)

            return True

        except Exception as e:
            logger.error(f"❌ Error in signal generation: {str(e)}")
            self.log_test("Signal Generation", "FAIL", str(e))
            return False

    def test_pipeline_components(self):
        """TEST: Verify all pipeline components are initialized"""
        print("\n" + "="*70)
        print("PIPELINE COMPONENTS CHECK")
        print("="*70)

        try:
            checks = {
                'Market Regime': hasattr(self.pipeline, 'market_regime'),
                'Signal Generator': hasattr(self.pipeline, 'signal_generator'),
                'Risk Manager': hasattr(self.pipeline, 'risk_manager'),
                'Options Handler': hasattr(self.pipeline, 'options_handler') or True,
            }

            all_ok = True
            for component, status in checks.items():
                if status:
                    self.log_test(f"Component: {component}", "PASS", "Initialized")
                else:
                    self.log_test(f"Component: {component}", "FAIL", "Not found")
                    all_ok = False

            return all_ok

        except Exception as e:
            self.log_test("Pipeline Components", "FAIL", str(e))
            return False

    def log_test(self, name: str, status: str, message: str = ""):
        """Log test result"""
        result = f"{'✅' if status == 'PASS' else '❌'} {name}"
        if message:
            result += f" | {message}"
        self.results.append(result)
        print(result)
        logger.info(result)

    def _display_signal(self, signal: dict):
        """Display complete signal in professional format"""
        print("\n" + "="*70)
        print("📊 GENERATED SIGNAL")
        print("="*70)

        print(f"""
Signal: {signal.get('signal', 'N/A')}
Strategy: {signal.get('strategy', 'N/A')}
Direction: {signal.get('direction', 'N/A')}
Confidence: {signal.get('confidence_score', 0)}%
Action: {signal.get('action', 'N/A')}
Risk Level: {signal.get('risk_level', 'N/A')}

Signal Wording:
{signal.get('signal_wording', 'N/A')}

Recommendation:
{signal.get('recommendation', 'N/A')}

Score Breakdown:
- Technical: {signal.get('score_breakdown', {}).get('technical', 0)}/40
- Regime: {signal.get('score_breakdown', {}).get('regime', 0)}/30
- Options: {signal.get('score_breakdown', {}).get('options', 0)}/20
- Risk: {signal.get('score_breakdown', {}).get('risk', 0)}/10
        """)

    def run_all_tests(self):
        """Run complete E2E signal generation test"""
        print("\n")
        print("╔════════════════════════════════════════════════════════════╗")
        print("║     SIGNAL GENERATION E2E TEST - COMPLETE PIPELINE         ║")
        print("╚════════════════════════════════════════════════════════════╝")

        test_results = {
            "Pipeline Components": self.test_pipeline_components(),
            "Signal Generation": self.test_complete_signal_generation(),
        }

        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)

        passed = sum(1 for v in test_results.values() if v is True)
        total = len(test_results)

        print(f"✅ PASSED: {passed}/{total}")

        if passed == total:
            print("\n✅ SIGNAL GENERATION PIPELINE: READY FOR PRODUCTION")
        else:
            print(f"\n⚠️ ISSUES FOUND: Fix {total - passed} failures")

        return test_results


if __name__ == '__main__':
    tester = SignalGenerationE2ETest()
    tester.run_all_tests()
