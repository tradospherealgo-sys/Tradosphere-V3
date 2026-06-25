"""
Angel One Options Chain Handler - REAL DATA ONLY
Fetches live options chain data from Angel One SmartAPI
"""

from typing import Dict, List, Optional
from datetime import datetime
from logger_config import get_logger
from options_chain import OptionsChain

logger = get_logger(__name__)


class AngelOneOptionsHandler:
    """Handle options chain fetching and processing from Angel One - LIVE DATA"""

    def __init__(self, smartapi_client, symbol: str, expiry_date: str):
        """
        Initialize options handler

        Args:
            smartapi_client: SmartConnect client instance (REQUIRED - NOT OPTIONAL)
            symbol: Stock/index symbol (e.g., 'NIFTY50', 'BANKNIFTY')
            expiry_date: Expiry date (format: '25JUN2026')
        """
        if not smartapi_client:
            raise ValueError("❌ SmartAPI client is REQUIRED - No mock data allowed")

        self.client = smartapi_client
        self.symbol = symbol
        self.expiry_date = expiry_date
        self.chain = None
        self.spot_price = None
        logger.info(f"✅ Angel One Options Handler initialized | Symbol: {symbol} | Expiry: {expiry_date}")

    def fetch_options_chain(self, spot_price: float) -> Dict:
        """
        Fetch REAL options chain from Angel One SmartAPI

        LIVE API CALL - Fetches actual market data

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
            logger.info(f"📡 FETCHING LIVE OPTIONS CHAIN: {self.symbol} | Expiry: {self.expiry_date} | Spot: {spot_price}")

            if not self.client:
                raise ValueError("❌ SmartAPI client not available - Cannot fetch real data")

            # REAL Angel One API Call - getOptionChain
            chain_response = self.client.getOptionChain(
                mode="FULL",
                exchangeTokens={"NFO": [self._get_nfo_token(self.symbol, self.expiry_date)]},
                strikePrice=""
            )

            if not chain_response or not chain_response.get('status'):
                logger.error(f"❌ Angel One API returned empty response")
                raise Exception("Empty response from Angel One API")

            # Parse live response
            live_data = self._parse_live_response(chain_response)

            self.spot_price = spot_price
            logger.info(f"✅ LIVE OPTIONS CHAIN FETCHED: {self.symbol} | {len(live_data['strikeDetails'])} strikes")

            return {
                'fetched': True,
                'data': live_data,
                'timestamp': datetime.now().isoformat(),
                'source': 'Angel One SmartAPI (LIVE)'
            }

        except Exception as e:
            logger.error(f"❌ Error fetching live options chain: {str(e)}")
            return {
                'fetched': False,
                'data': {'expiryDates': [], 'strikeDetails': []},
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def _get_nfo_token(self, symbol: str, expiry_date: str) -> str:
        """
        Get NFO token for symbol-expiry combination

        Maps symbol to actual Angel One exchange token
        """
        # Common NFO tokens - should be fetched from Angel One's symbol master
        nfo_tokens = {
            'NIFTY50': '99926000',  # NIFTY 50 Index
            'BANKNIFTY': '99926009',  # BANK NIFTY Index
            'FINNIFTY': '99926037',  # FIN NIFTY Index
        }

        token = nfo_tokens.get(symbol)
        if not token:
            logger.warning(f"⚠️ Unknown NFO token for {symbol}, attempting direct call")
            return symbol

        return token

    def _parse_live_response(self, api_response: Dict) -> Dict:
        """
        Parse live Angel One API response into standard format

        Handles real API response structure from Angel One
        """
        try:
            strike_details = []

            # Parse actual Angel One response structure
            fetched = api_response.get('fetched', False)
            if not fetched:
                return {'expiryDates': [], 'strikeDetails': []}

            data = api_response.get('data', {})
            strikes = data.get('strikes', [])

            for strike_data in strikes:
                # Extract real live prices from Angel One
                strike_entry = {
                    'strike': int(strike_data.get('strike_price', 0)),
                    'callSymbol': strike_data.get('call_symbol', ''),
                    'putSymbol': strike_data.get('put_symbol', ''),
                    'callLTP': float(strike_data.get('call_ltp', 0)),
                    'putLTP': float(strike_data.get('put_ltp', 0)),
                    'callOI': int(strike_data.get('call_oi', 0)),
                    'putOI': int(strike_data.get('put_oi', 0)),
                    'callBid': float(strike_data.get('call_bid', 0)),
                    'callAsk': float(strike_data.get('call_ask', 0)),
                    'callBidQty': int(strike_data.get('call_bid_qty', 0)),
                    'callAskQty': int(strike_data.get('call_ask_qty', 0)),
                    'callVolume': int(strike_data.get('call_volume', 0)),
                    'putBid': float(strike_data.get('put_bid', 0)),
                    'putAsk': float(strike_data.get('put_ask', 0)),
                    'putBidQty': int(strike_data.get('put_bid_qty', 0)),
                    'putAskQty': int(strike_data.get('put_ask_qty', 0)),
                    'putVolume': int(strike_data.get('put_volume', 0)),
                }

                strike_details.append(strike_entry)

            return {
                'expiryDates': [self.expiry_date],
                'strikeDetails': strike_details,
                'fetchTime': datetime.now().isoformat(),
                'source': 'Angel One SmartAPI'
            }

        except Exception as e:
            logger.error(f"❌ Error parsing live response: {str(e)}")
            return {'expiryDates': [], 'strikeDetails': []}

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
