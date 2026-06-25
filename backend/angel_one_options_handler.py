"""
Angel One Options Chain Handler
Fetches options chain data from Angel One SmartAPI and parses it for analysis
"""

from typing import Dict, List, Optional
from datetime import datetime
from logger_config import get_logger
from options_chain import OptionsChain

logger = get_logger(__name__)


class AngelOneOptionsHandler:
    """Handle options chain fetching and processing from Angel One"""

    def __init__(self, smartapi_client, symbol: str, expiry_date: str):
        """
        Initialize options handler

        Args:
            smartapi_client: SmartConnect client instance
            symbol: Stock/index symbol (e.g., 'NIFTY50', 'BANKNIFTY')
            expiry_date: Expiry date (format: '25JUN2026')
        """
        self.client = smartapi_client
        self.symbol = symbol
        self.expiry_date = expiry_date
        self.chain = None
        self.spot_price = None

    def fetch_options_chain(self, spot_price: float) -> Dict:
        """
        Fetch options chain from Angel One SmartAPI

        Returns:
        {
            'fetched': True/False,
            'data': {
                'expiryDates': [...],
                'strikeDetails': [...]
            },
            'error': error message if failed
        }
        """
        try:
            logger.info(f"📡 Fetching options chain for {self.symbol} | Expiry: {self.expiry_date}")

            # Get option chain from SmartAPI
            # Note: Actual API call depends on SmartAPI implementation
            # This is a template structure

            response = {
                'fetched': False,
                'data': {
                    'expiryDates': [],
                    'strikeDetails': []
                }
            }

            # Fetch from Angel One (pseudo-code, actual implementation varies)
            try:
                # Example: self.client.getOptionChain(...)
                # For now, return template structure
                logger.warning("⚠️ Using mock options chain - Connect to real Angel One API")

                # Mock response structure
                response = {
                    'fetched': True,
                    'data': {
                        'expiryDates': [self.expiry_date],
                        'strikeDetails': self._generate_mock_chain(spot_price)
                    }
                }

            except Exception as e:
                logger.error(f"❌ Angel One API error: {str(e)}")
                response['error'] = str(e)

            self.spot_price = spot_price
            return response

        except Exception as e:
            logger.error(f"❌ Error fetching options chain: {str(e)}")
            return {
                'fetched': False,
                'data': {'expiryDates': [], 'strikeDetails': []},
                'error': str(e)
            }

    def parse_chain_and_analyze(self, chain_response: Dict, expiry_days: int = 7) -> Dict:
        """
        Parse options chain and perform complete analysis

        Returns comprehensive options analysis with all features
        """
        try:
            if not chain_response.get('fetched'):
                return {'error': 'Chain data not available'}

            # Create OptionsChain instance
            self.chain = OptionsChain(self.spot_price, self.symbol, expiry_days)

            # Parse chain data
            parsed = self.chain.parse_chain_from_smartapi(chain_response)
            if 'error' in parsed:
                return parsed

            # Perform all analyses
            analysis = {
                'symbol': self.symbol,
                'spot_price': self.spot_price,
                'expiry_date': self.expiry_date,
                'timestamp': datetime.now().isoformat(),
                'chain_summary': self.chain.get_chain_summary(),
                'oi_analysis': self.chain.get_comprehensive_oi_analysis(),
                'expected_move': self.chain.calculate_expected_move_for_stock(),
                'skew': self.chain.analyze_skew(),
                'atm_options': self.chain.get_atm_options(width=3)
            }

            logger.info(f"✅ Options analysis complete: {self.symbol} | {len(parsed['strikes'])} strikes")
            return analysis

        except Exception as e:
            logger.error(f"❌ Error analyzing chain: {str(e)}")
            return {'error': str(e)}

    def get_signal_input_data(self) -> Dict:
        """
        Extract data needed for signal generation

        Returns data formatted for composite_signal_generator
        """
        try:
            if not self.chain:
                return {'error': 'Chain not analyzed yet'}

            # Get OI buildup data
            oi_data = self.chain.get_comprehensive_oi_analysis()
            oi_buildup = oi_data.get('oi_buildup', {}).get('direction')

            # Get market regime data (will be populated by market_regime.py)
            # For now, return structure

            return {
                'symbol': self.symbol,
                'spot_price': self.spot_price,
                'options_context': {
                    'pcr': oi_data.get('pcr', {}),
                    'max_pain': oi_data.get('max_pain', {}),
                    'max_pain_bias': oi_data.get('max_pain', {}).get('bias'),
                    'oi_buildup_direction': oi_buildup,
                    'skew_direction': self.chain.analyze_skew().get('skew_direction'),
                    'expected_move': self.chain.calculate_expected_move_for_stock()
                },
                'atm_strike': self.chain.get_atm_options().get('atm_strike'),
                'atm_iv': self._get_atm_iv()
            }

        except Exception as e:
            logger.error(f"❌ Error preparing signal input: {str(e)}")
            return {'error': str(e)}

    def _get_atm_iv(self) -> float:
        """Get ATM IV"""
        try:
            atm_options = self.chain.get_atm_options()
            if 'options' in atm_options and len(atm_options['options']) > 0:
                atm_strike = atm_options['options'][0]
                return atm_strike['call']['iv'] / 100.0
            return 0.25
        except:
            return 0.25

    def _generate_mock_chain(self, spot_price: float) -> List[Dict]:
        """Generate mock options chain for testing"""
        strikes = []
        base_strike = int(spot_price / 100) * 100  # Round to nearest 100

        for offset in [-400, -300, -200, -100, 0, 100, 200, 300, 400]:
            strike = base_strike + offset

            call_price = max(0, spot_price - strike + 50)
            put_price = max(0, strike - spot_price + 50)

            strikes.append({
                'strike': strike,
                'callSymbol': f'{self.symbol}{strike}CE',
                'putSymbol': f'{self.symbol}{strike}PE',
                'callLTP': round(call_price, 2),
                'putLTP': round(put_price, 2),
                'callOI': 500000 + (abs(offset) * 1000),
                'putOI': 450000 + (abs(offset) * 1000),
                'callBid': round(call_price - 0.5, 2),
                'callAsk': round(call_price + 0.5, 2),
                'callBidQty': 50,
                'callAskQty': 50,
                'callVolume': 1000 + (abs(offset) // 100) * 100,
                'putVolume': 800 + (abs(offset) // 100) * 100,
                'putBid': round(put_price - 0.5, 2),
                'putAsk': round(put_price + 0.5, 2),
                'putBidQty': 50,
                'putAskQty': 50
            })

        return strikes

    def track_snapshot(self):
        """Track current chain state for historical analysis"""
        try:
            if self.chain:
                self.chain.track_oi_history()
                logger.info(f"✅ Options chain snapshot tracked for {self.symbol}")
        except Exception as e:
            logger.error(f"❌ Error tracking snapshot: {str(e)}")

    def get_greeks_ladder(self, num_strikes: int = 9) -> Dict:
        """Get Greeks ladder for visualization"""
        try:
            if not self.chain:
                return {'error': 'Chain not analyzed yet'}

            strikes = [s['strike'] for s in self.chain.chain_data.get('strikes', [])][
                -num_strikes // 2 : num_strikes // 2 + 1
            ]
            return self.chain.build_greeks_ladder(strikes)

        except Exception as e:
            logger.error(f"❌ Error building Greeks ladder: {str(e)}")
            return {'error': str(e)}
