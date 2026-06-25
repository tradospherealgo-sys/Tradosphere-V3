"""
E2E Test Suite for Options Chain Module (All 9 Features)
Complete audit and validation
"""

import sys
import json
from datetime import datetime
from options_chain import GreeksCalculator, OptionsChain
from logger_config import get_logger

logger = get_logger(__name__)

# Test data
TEST_SPOT = 23450.25
TEST_SYMBOL = "NIFTY50"
TEST_EXPIRY_DAYS = 7
TEST_RISK_FREE_RATE = 0.06

class OptionsChainE2ETest:
    """Complete E2E test suite"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def log_test(self, name: str, status: str, message: str = ""):
        """Log test result"""
        result = f"{'✅' if status == 'PASS' else '❌'} {name}"
        if message:
            result += f" | {message}"
        self.results.append(result)
        print(result)

        if status == 'PASS':
            self.passed += 1
        else:
            self.failed += 1

    def test_greeks_calculator(self):
        """TEST 1: Greeks Calculator basic functions"""
        print("\n" + "="*70)
        print("TEST 1: Greeks Calculator Functions")
        print("="*70)

        try:
            # Test Delta
            delta = GreeksCalculator.calculate_delta(100, 100, 0.25, 0.06, 0.2, 'CALL')
            assert 0 <= delta <= 1, f"Delta out of range: {delta}"
            self.log_test("Delta Calculation", "PASS", f"Delta={delta:.4f}")

            # Test Gamma
            gamma = GreeksCalculator.calculate_gamma(100, 100, 0.25, 0.06, 0.2)
            assert gamma >= 0, f"Gamma negative: {gamma}"
            self.log_test("Gamma Calculation", "PASS", f"Gamma={gamma:.6f}")

            # Test Theta
            theta = GreeksCalculator.calculate_theta(100, 100, 0.25, 0.06, 0.2, 'CALL')
            self.log_test("Theta Calculation", "PASS", f"Theta={theta:.4f}")

            # Test Vega
            vega = GreeksCalculator.calculate_vega(100, 100, 0.25, 0.06, 0.2)
            assert vega >= 0, f"Vega negative: {vega}"
            self.log_test("Vega Calculation", "PASS", f"Vega={vega:.4f}")

            # Test IV Calculation
            call_price = GreeksCalculator.calculate_call_price(100, 100, 0.25, 0.06, 0.2)
            iv = GreeksCalculator.calculate_iv(call_price, 100, 100, 0.25, 0.06, 'CALL')
            assert 0 <= iv <= 5, f"IV out of range: {iv}"
            self.log_test("IV Calculation (Brent's method)", "PASS", f"IV={iv:.4f}")

            # Test Rho
            rho = GreeksCalculator.calculate_rho(100, 100, 0.25, 0.06, 0.2, 'CALL')
            self.log_test("Rho Calculation", "PASS", f"Rho={rho:.4f}")

            # Test Expected Move
            exp_move = GreeksCalculator.calculate_expected_move(100, 0.25, 0.2)
            assert 'dollar_move' in exp_move and 'percent_move' in exp_move
            self.log_test("Expected Move Calculation", "PASS", f"Move=${exp_move['dollar_move']:.2f}")

        except Exception as e:
            self.log_test("Greeks Calculator", "FAIL", str(e))

    def test_options_chain_initialization(self):
        """TEST 2: Options Chain Initialization"""
        print("\n" + "="*70)
        print("TEST 2: Options Chain Initialization")
        print("="*70)

        try:
            chain = OptionsChain(TEST_SPOT, TEST_SYMBOL, TEST_EXPIRY_DAYS, TEST_RISK_FREE_RATE)
            assert chain.spot_price == TEST_SPOT
            assert chain.symbol == TEST_SYMBOL
            assert chain.expiry_days == TEST_EXPIRY_DAYS
            self.log_test("Chain Object Creation", "PASS", f"Spot={chain.spot_price}")
        except Exception as e:
            self.log_test("Chain Object Creation", "FAIL", str(e))

    def test_chain_parsing(self):
        """TEST 3: Options Chain Parsing from API"""
        print("\n" + "="*70)
        print("TEST 3: Chain Data Parsing")
        print("="*70)

        try:
            chain = OptionsChain(TEST_SPOT, TEST_SYMBOL, TEST_EXPIRY_DAYS, TEST_RISK_FREE_RATE)

            # Mock API response
            mock_response = {
                'fetched': True,
                'data': {
                    'strikeDetails': [
                        {
                            'strike': 23000,
                            'callSymbol': 'NIFTY23000CE',
                            'putSymbol': 'NIFTY23000PE',
                            'callLTP': 485.50,
                            'putLTP': 12.25,
                            'callOI': 1250000,
                            'putOI': 980000,
                            'callBid': 483.00,
                            'callAsk': 487.00,
                            'callBidQty': 100,
                            'callAskQty': 100,
                            'callVolume': 5000,
                            'putVolume': 3000
                        },
                        {
                            'strike': 23500,
                            'callSymbol': 'NIFTY23500CE',
                            'putSymbol': 'NIFTY23500PE',
                            'callLTP': 145.75,
                            'putLTP': 42.25,
                            'callOI': 2150000,
                            'putOI': 1850000,
                            'callBid': 144.50,
                            'callAsk': 147.00,
                            'callBidQty': 150,
                            'callAskQty': 150,
                            'callVolume': 8500,
                            'putVolume': 7200
                        }
                    ]
                }
            }

            result = chain.parse_chain_from_smartapi(mock_response)
            assert 'strikes' in result
            assert len(result['strikes']) == 2
            self.log_test("Chain Parsing", "PASS", f"Parsed {len(result['strikes'])} strikes")

            # Verify Greeks are calculated
            for strike in result['strikes']:
                assert 'call' in strike and 'put' in strike
                assert 'delta' in strike['call'] and 'iv' in strike['call']
                assert 'theta' in strike['put'] and 'vega' in strike['put']

            self.log_test("Greeks Calculation in Parse", "PASS", "All Greeks present")

        except Exception as e:
            self.log_test("Chain Parsing", "FAIL", str(e))

    def test_feature_1_iv_rank(self):
        """TEST 4: Feature #1 - IV Rank/Percentile"""
        print("\n" + "="*70)
        print("TEST 4: Feature #1 - IV Rank/Percentile")
        print("="*70)

        try:
            chain = OptionsChain(TEST_SPOT, TEST_SYMBOL, TEST_EXPIRY_DAYS)

            # Create mock historical IV data (252 trading days)
            historical_iv = [0.15 + 0.05 * (i % 10) / 10 for i in range(252)]

            # Pass current_iv since chain data is empty
            result = chain.calculate_iv_rank_percentile(historical_iv, current_iv=0.17)
            assert 'iv_rank' in result and 'iv_percentile' in result
            assert isinstance(result['iv_rank'], (int, float)) or result['iv_rank'] == 'N/A'
            self.log_test("IV Rank/Percentile", "PASS", f"Rank={result.get('iv_rank')}%, Pctl={result.get('iv_percentile')}%")

        except Exception as e:
            self.log_test("IV Rank/Percentile", "FAIL", str(e))

    def test_feature_2_rho(self):
        """TEST 5: Feature #2 - Rho"""
        print("\n" + "="*70)
        print("TEST 5: Feature #2 - Rho")
        print("="*70)

        try:
            chain = OptionsChain(TEST_SPOT, TEST_SYMBOL, TEST_EXPIRY_DAYS)

            # Need to have parsed chain first
            mock_response = {
                'fetched': True,
                'data': {
                    'strikeDetails': [
                        {'strike': 23450, 'callSymbol': 'N1', 'putSymbol': 'N2',
                         'callLTP': 100, 'putLTP': 50, 'callOI': 1000000, 'putOI': 900000,
                         'callBid': 99, 'callAsk': 101, 'callBidQty': 100, 'callAskQty': 100,
                         'callVolume': 5000, 'putVolume': 4000}
                    ]
                }
            }

            chain.parse_chain_from_smartapi(mock_response)
            result = chain.calculate_rho_for_chain()
            assert 'options' in result
            assert len(result['options']) > 0
            self.log_test("Rho Calculation", "PASS", f"Calculated for {len(result['options'])} strikes")

        except Exception as e:
            self.log_test("Rho Calculation", "FAIL", str(e))

    def test_feature_3_expected_move(self):
        """TEST 6: Feature #3 - Expected Move"""
        print("\n" + "="*70)
        print("TEST 6: Feature #3 - Expected Move")
        print("="*70)

        try:
            chain = OptionsChain(TEST_SPOT, TEST_SYMBOL, TEST_EXPIRY_DAYS)

            mock_response = {
                'fetched': True,
                'data': {
                    'strikeDetails': [
                        {'strike': 23450, 'callSymbol': 'N1', 'putSymbol': 'N2',
                         'callLTP': 100, 'putLTP': 50, 'callOI': 1000000, 'putOI': 900000,
                         'callBid': 99, 'callAsk': 101, 'callBidQty': 100, 'callAskQty': 100,
                         'callVolume': 5000, 'putVolume': 4000}
                    ]
                }
            }

            chain.parse_chain_from_smartapi(mock_response)
            result = chain.calculate_expected_move_for_stock()
            assert 'expected_move_dollar' in result and 'expected_move_percent' in result
            assert 'support_1std' in result and 'resistance_1std' in result
            self.log_test("Expected Move", "PASS", f"1STD Move=${result['expected_move_dollar']:.2f} ({result['expected_move_percent']:.2f}%)")

        except Exception as e:
            self.log_test("Expected Move", "FAIL", str(e))

    def test_feature_4_portfolio_greeks(self):
        """TEST 7: Feature #4 - Greeks Aggregation"""
        print("\n" + "="*70)
        print("TEST 7: Feature #4 - Portfolio Greeks Aggregation")
        print("="*70)

        try:
            chain = OptionsChain(TEST_SPOT, TEST_SYMBOL, TEST_EXPIRY_DAYS)

            mock_response = {
                'fetched': True,
                'data': {
                    'strikeDetails': [
                        {'strike': 23450, 'callSymbol': 'N1', 'putSymbol': 'N2',
                         'callLTP': 100, 'putLTP': 50, 'callOI': 1000000, 'putOI': 900000,
                         'callBid': 99, 'callAsk': 101, 'callBidQty': 100, 'callAskQty': 100,
                         'callVolume': 5000, 'putVolume': 4000}
                    ]
                }
            }

            chain.parse_chain_from_smartapi(mock_response)

            positions = [
                {'strike': 23450, 'type': 'CALL', 'quantity': 2, 'price': 100}
            ]

            result = chain.calculate_portfolio_greeks(positions)
            assert 'total_delta' in result and 'total_gamma' in result
            assert 'total_theta' in result and 'total_vega' in result
            self.log_test("Portfolio Greeks", "PASS", f"Delta={result['total_delta']}, Theta={result['total_theta']:.2f}")

        except Exception as e:
            self.log_test("Portfolio Greeks", "FAIL", str(e))

    def test_feature_5_skew(self):
        """TEST 8: Feature #5 - Skew Analysis"""
        print("\n" + "="*70)
        print("TEST 8: Feature #5 - Skew Analysis")
        print("="*70)

        try:
            chain = OptionsChain(TEST_SPOT, TEST_SYMBOL, TEST_EXPIRY_DAYS)

            mock_response = {
                'fetched': True,
                'data': {
                    'strikeDetails': [
                        {'strike': 23400, 'callSymbol': 'N1', 'putSymbol': 'N2',
                         'callLTP': 120, 'putLTP': 40, 'callOI': 1000000, 'putOI': 900000,
                         'callBid': 119, 'callAsk': 121, 'callBidQty': 100, 'callAskQty': 100,
                         'callVolume': 5000, 'putVolume': 4000},
                        {'strike': 23450, 'callSymbol': 'N3', 'putSymbol': 'N4',
                         'callLTP': 100, 'putLTP': 50, 'callOI': 1000000, 'putOI': 900000,
                         'callBid': 99, 'callAsk': 101, 'callBidQty': 100, 'callAskQty': 100,
                         'callVolume': 5000, 'putVolume': 4000},
                        {'strike': 23500, 'callSymbol': 'N5', 'putSymbol': 'N6',
                         'callLTP': 80, 'putLTP': 60, 'callOI': 1000000, 'putOI': 900000,
                         'callBid': 79, 'callAsk': 81, 'callBidQty': 100, 'callAskQty': 100,
                         'callVolume': 5000, 'putVolume': 4000}
                    ]
                }
            }

            chain.parse_chain_from_smartapi(mock_response)
            result = chain.analyze_skew()
            assert 'skew_direction' in result and 'skew_intensity' in result
            self.log_test("Skew Analysis", "PASS", f"Direction={result['skew_direction']}, Intensity={result['skew_intensity']}")

        except Exception as e:
            self.log_test("Skew Analysis", "FAIL", str(e))

    def test_feature_6_oi_analysis(self):
        """TEST 9: Feature #6 - PCR/Max Pain/OI Buildup"""
        print("\n" + "="*70)
        print("TEST 9: Feature #6 - PCR/Max Pain/OI Buildup")
        print("="*70)

        try:
            chain = OptionsChain(TEST_SPOT, TEST_SYMBOL, TEST_EXPIRY_DAYS)

            mock_response = {
                'fetched': True,
                'data': {
                    'strikeDetails': [
                        {'strike': 23400, 'callSymbol': 'N1', 'putSymbol': 'N2',
                         'callLTP': 120, 'putLTP': 40, 'callOI': 800000, 'putOI': 1200000,
                         'callBid': 119, 'callAsk': 121, 'callBidQty': 100, 'callAskQty': 100,
                         'callVolume': 5000, 'putVolume': 4000},
                        {'strike': 23450, 'callSymbol': 'N3', 'putSymbol': 'N4',
                         'callLTP': 100, 'putLTP': 50, 'callOI': 2000000, 'putOI': 1500000,
                         'callBid': 99, 'callAsk': 101, 'callBidQty': 100, 'callAskQty': 100,
                         'callVolume': 5000, 'putVolume': 4000}
                    ]
                }
            }

            chain.parse_chain_from_smartapi(mock_response)
            result = chain.get_comprehensive_oi_analysis()
            assert 'pcr' in result and 'max_pain' in result and 'oi_buildup' in result
            self.log_test("OI Analysis (PCR/Max Pain/Buildup)", "PASS", f"PCR={result['pcr'].get('pcr', 'N/A')}")

        except Exception as e:
            self.log_test("OI Analysis", "FAIL", str(e))

    def test_feature_7_lot_size(self):
        """TEST 10: Feature #7 - Lot Size Handling"""
        print("\n" + "="*70)
        print("TEST 10: Feature #7 - Lot Size Handling")
        print("="*70)

        try:
            chain = OptionsChain(TEST_SPOT, TEST_SYMBOL, TEST_EXPIRY_DAYS)
            chain.set_lot_size(75)  # NIFTY lot size

            mock_response = {
                'fetched': True,
                'data': {
                    'strikeDetails': [
                        {'strike': 23450, 'callSymbol': 'N1', 'putSymbol': 'N2',
                         'callLTP': 100, 'putLTP': 50, 'callOI': 1000000, 'putOI': 900000,
                         'callBid': 99, 'callAsk': 101, 'callBidQty': 100, 'callAskQty': 100,
                         'callVolume': 5000, 'putVolume': 4000}
                    ]
                }
            }

            chain.parse_chain_from_smartapi(mock_response)
            result = chain.get_greeks_with_lot_size(23450, 'CALL')
            assert 'delta_per_lot' in result and result['lot_size'] == 75
            self.log_test("Lot Size Handling", "PASS", f"Lot Size=75, Delta per lot={result['delta_per_lot']}")

        except Exception as e:
            self.log_test("Lot Size Handling", "FAIL", str(e))

    def test_feature_8_oi_history(self):
        """TEST 11: Feature #8 - Historical OI Tracking"""
        print("\n" + "="*70)
        print("TEST 11: Feature #8 - Historical OI Tracking")
        print("="*70)

        try:
            chain = OptionsChain(TEST_SPOT, TEST_SYMBOL, TEST_EXPIRY_DAYS)

            mock_response = {
                'fetched': True,
                'data': {
                    'strikeDetails': [
                        {'strike': 23450, 'callSymbol': 'N1', 'putSymbol': 'N2',
                         'callLTP': 100, 'putLTP': 50, 'callOI': 1000000, 'putOI': 900000,
                         'callBid': 99, 'callAsk': 101, 'callBidQty': 100, 'callAskQty': 100,
                         'callVolume': 5000, 'putVolume': 4000}
                    ]
                }
            }

            chain.parse_chain_from_smartapi(mock_response)
            chain.track_oi_history("2026-06-25T09:15:00")

            # Modify OI and track again
            mock_response['data']['strikeDetails'][0]['callOI'] = 1050000
            chain.parse_chain_from_smartapi(mock_response)
            chain.track_oi_history("2026-06-25T09:30:00")

            assert hasattr(chain, 'oi_history') and len(chain.oi_history) == 2
            self.log_test("OI History Tracking", "PASS", f"Tracked {len(chain.oi_history)} snapshots")

        except Exception as e:
            self.log_test("OI History Tracking", "FAIL", str(e))

    def test_feature_9_greeks_ladder(self):
        """TEST 12: Feature #9 - Greeks Ladder"""
        print("\n" + "="*70)
        print("TEST 12: Feature #9 - Greeks Ladder")
        print("="*70)

        try:
            chain = OptionsChain(TEST_SPOT, TEST_SYMBOL, TEST_EXPIRY_DAYS)

            mock_response = {
                'fetched': True,
                'data': {
                    'strikeDetails': [
                        {'strike': 23400, 'callSymbol': 'N1', 'putSymbol': 'N2',
                         'callLTP': 120, 'putLTP': 40, 'callOI': 800000, 'putOI': 1200000,
                         'callBid': 119, 'callAsk': 121, 'callBidQty': 100, 'callAskQty': 100,
                         'callVolume': 5000, 'putVolume': 4000},
                        {'strike': 23450, 'callSymbol': 'N3', 'putSymbol': 'N4',
                         'callLTP': 100, 'putLTP': 50, 'callOI': 2000000, 'putOI': 1500000,
                         'callBid': 99, 'callAsk': 101, 'callBidQty': 100, 'callAskQty': 100,
                         'callVolume': 5000, 'putVolume': 4000},
                        {'strike': 23500, 'callSymbol': 'N5', 'putSymbol': 'N6',
                         'callLTP': 80, 'putLTP': 60, 'callOI': 900000, 'putOI': 800000,
                         'callBid': 79, 'callAsk': 81, 'callBidQty': 100, 'callAskQty': 100,
                         'callVolume': 5000, 'putVolume': 4000}
                    ]
                }
            }

            chain.parse_chain_from_smartapi(mock_response)
            result = chain.build_greeks_ladder()
            assert 'ladder' in result and len(result['ladder']) > 0
            self.log_test("Greeks Ladder", "PASS", f"Built ladder with {len(result['ladder'])} strikes")

        except Exception as e:
            self.log_test("Greeks Ladder", "FAIL", str(e))

    def run_all_tests(self):
        """Run complete E2E test suite"""
        print("\n")
        print("╔" + "="*68 + "╗")
        print("║" + " "*15 + "OPTIONS CHAIN E2E TEST SUITE" + " "*25 + "║")
        print("╚" + "="*68 + "╝")

        self.test_greeks_calculator()
        self.test_options_chain_initialization()
        self.test_chain_parsing()
        self.test_feature_1_iv_rank()
        self.test_feature_2_rho()
        self.test_feature_3_expected_move()
        self.test_feature_4_portfolio_greeks()
        self.test_feature_5_skew()
        self.test_feature_6_oi_analysis()
        self.test_feature_7_lot_size()
        self.test_feature_8_oi_history()
        self.test_feature_9_greeks_ladder()

        # Print summary
        print("\n")
        print("╔" + "="*68 + "╗")
        print("║" + " "*20 + "AUDIT SUMMARY" + " "*35 + "║")
        print("╠" + "="*68 + "╣")
        print(f"║ ✅ PASSED: {self.passed:<60} ║")
        print(f"║ ❌ FAILED: {self.failed:<60} ║")
        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0
        print(f"║ 📊 SUCCESS RATE: {success_rate:.1f}% ({self.passed}/{total} tests)" + " " * (68 - len(f"SUCCESS RATE: {success_rate:.1f}% ({self.passed}/{total} tests)") - 8) + "║")
        print("╚" + "="*68 + "╝")

        return {
            'passed': self.passed,
            'failed': self.failed,
            'total': total,
            'success_rate': success_rate,
            'results': self.results
        }


if __name__ == '__main__':
    tester = OptionsChainE2ETest()
    results = tester.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if results['failed'] == 0 else 1)
