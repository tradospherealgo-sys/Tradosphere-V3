"""
Options Chain Module - Complete Options Data Handler
Fetches, parses, and analyzes options chain data with Greeks, IV, and pricing
"""

import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime
from logger_config import get_logger

logger = get_logger(__name__)


class GreeksCalculator:
    """Calculate Black-Scholes Greeks for options"""

    @staticmethod
    def calculate_d1_d2(S, K, T, r, sigma):
        """Calculate d1 and d2 for Black-Scholes"""
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return d1, d2

    @staticmethod
    def normal_pdf(x):
        """Standard normal probability density function"""
        return (1 / np.sqrt(2 * np.pi)) * np.exp(-0.5 * x ** 2)

    @staticmethod
    def normal_cdf(x):
        """Standard normal cumulative distribution"""
        return (1 + np.tanh(np.sqrt(2 / np.pi) * (x + 0.044715 * x ** 3))) / 2

    @staticmethod
    def calculate_delta(S, K, T, r, sigma, option_type='CALL'):
        """Calculate option delta"""
        if T <= 0:
            return 1.0 if option_type == 'CALL' and S > K else (0.0 if option_type == 'CALL' else 1.0)

        d1, _ = GreeksCalculator.calculate_d1_d2(S, K, T, r, sigma)
        if option_type == 'CALL':
            return GreeksCalculator.normal_cdf(d1)
        else:
            return GreeksCalculator.normal_cdf(d1) - 1

    @staticmethod
    def calculate_gamma(S, K, T, r, sigma):
        """Calculate option gamma"""
        if T <= 0:
            return 0.0

        d1, _ = GreeksCalculator.calculate_d1_d2(S, K, T, r, sigma)
        return GreeksCalculator.normal_pdf(d1) / (S * sigma * np.sqrt(T))

    @staticmethod
    def calculate_theta(S, K, T, r, sigma, option_type='CALL'):
        """Calculate option theta (per day)"""
        if T <= 0:
            return 0.0

        d1, d2 = GreeksCalculator.calculate_d1_d2(S, K, T, r, sigma)

        if option_type == 'CALL':
            theta = (-S * GreeksCalculator.normal_pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * GreeksCalculator.normal_cdf(d2)
        else:
            theta = (-S * GreeksCalculator.normal_pdf(d1) * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * GreeksCalculator.normal_cdf(-d2)

        return theta / 365  # Convert to per day

    @staticmethod
    def calculate_vega(S, K, T, r, sigma):
        """Calculate option vega (per 1% change in IV)"""
        if T <= 0:
            return 0.0

        d1, _ = GreeksCalculator.calculate_d1_d2(S, K, T, r, sigma)
        return S * GreeksCalculator.normal_pdf(d1) * np.sqrt(T) / 100

    @staticmethod
    def calculate_iv(market_price, S, K, T, r, option_type='CALL', initial_guess=0.25):
        """Calculate implied volatility using Newton-Raphson"""
        sigma = initial_guess
        for _ in range(100):
            d1, d2 = GreeksCalculator.calculate_d1_d2(S, K, T, r, sigma)

            if option_type == 'CALL':
                price = S * GreeksCalculator.normal_cdf(d1) - K * np.exp(-r * T) * GreeksCalculator.normal_cdf(d2)
            else:
                price = K * np.exp(-r * T) * GreeksCalculator.normal_cdf(-d2) - S * GreeksCalculator.normal_cdf(-d1)

            vega = S * GreeksCalculator.normal_pdf(d1) * np.sqrt(T)

            if abs(vega) < 1e-10 or abs(price - market_price) < 1e-6:
                break

            sigma = sigma - (price - market_price) / vega
            sigma = max(0.001, min(sigma, 5.0))  # Keep sigma in reasonable range

        return max(0.001, min(sigma, 5.0))


class OptionsChain:
    """Complete options chain handler with pricing and analytics"""

    def __init__(self, spot_price: float, symbol: str, expiry_days: int = 7, risk_free_rate: float = 0.06):
        """
        Initialize options chain

        Args:
            spot_price: Current spot price
            symbol: Stock/index symbol
            expiry_days: Days to expiration
            risk_free_rate: Annual risk-free rate
        """
        self.spot_price = spot_price
        self.symbol = symbol
        self.expiry_days = expiry_days
        self.time_to_expiry = expiry_days / 365.0
        self.risk_free_rate = risk_free_rate
        self.chain_data = {}
        self.greeks = GreeksCalculator()

    def parse_chain_from_smartapi(self, chain_response: Dict) -> Dict:
        """
        Parse options chain data from Angel One SmartAPI response

        Expected format from SmartAPI:
        {
            'fetched': True,
            'data': {
                'expiryDates': ['25JUN2026', '02JUL2026'],
                'strikeDetails': [
                    {
                        'strike': 23000,
                        'callSymbol': '...',
                        'putSymbol': '...',
                        'callLTP': 450.50,
                        'putLTP': 12.25,
                        'callOI': 1250000,
                        'putOI': 980000,
                        'callIV': 0.18,
                        'putIV': 0.16,
                        'callBidQty': 100,
                        'callAskQty': 100,
                        'putBidQty': 100,
                        'putAskQty': 100,
                        'callVolume': 5000,
                        'putVolume': 3000
                    },
                    ...
                ]
            }
        }
        """
        try:
            if not chain_response.get('fetched'):
                logger.warning(f"⚠️ Chain data not fetched for {self.symbol}")
                return {'error': 'Chain data not available'}

            chain_data = chain_response.get('data', {})
            strike_details = chain_data.get('strikeDetails', [])

            parsed_chain = {
                'symbol': self.symbol,
                'spot_price': self.spot_price,
                'expiry_days': self.expiry_days,
                'fetch_timestamp': datetime.now().isoformat(),
                'strikes': []
            }

            for strike_data in strike_details:
                strike = strike_data.get('strike')
                call_price = strike_data.get('callLTP', 0)
                put_price = strike_data.get('putLTP', 0)

                # Calculate Greeks
                call_delta = self.greeks.calculate_delta(
                    self.spot_price, strike, self.time_to_expiry,
                    self.risk_free_rate, strike_data.get('callIV', 0.25), 'CALL'
                )
                put_delta = self.greeks.calculate_delta(
                    self.spot_price, strike, self.time_to_expiry,
                    self.risk_free_rate, strike_data.get('putIV', 0.25), 'PUT'
                )

                call_gamma = self.greeks.calculate_gamma(
                    self.spot_price, strike, self.time_to_expiry,
                    self.risk_free_rate, strike_data.get('callIV', 0.25)
                )

                call_theta = self.greeks.calculate_theta(
                    self.spot_price, strike, self.time_to_expiry,
                    self.risk_free_rate, strike_data.get('callIV', 0.25), 'CALL'
                )
                put_theta = self.greeks.calculate_theta(
                    self.spot_price, strike, self.time_to_expiry,
                    self.risk_free_rate, strike_data.get('putIV', 0.25), 'PUT'
                )

                call_vega = self.greeks.calculate_vega(
                    self.spot_price, strike, self.time_to_expiry,
                    self.risk_free_rate, strike_data.get('callIV', 0.25)
                )

                strike_entry = {
                    'strike': strike,
                    'atm_distance': strike - self.spot_price,
                    'atm_distance_pct': ((strike - self.spot_price) / self.spot_price) * 100,
                    'call': {
                        'symbol': strike_data.get('callSymbol', f'{self.symbol}C{strike}'),
                        'ltp': round(call_price, 2),
                        'bid': strike_data.get('callBid', 0),
                        'ask': strike_data.get('callAsk', 0),
                        'bid_qty': strike_data.get('callBidQty', 0),
                        'ask_qty': strike_data.get('callAskQty', 0),
                        'volume': strike_data.get('callVolume', 0),
                        'oi': strike_data.get('callOI', 0),
                        'iv': round(strike_data.get('callIV', 0.25), 4),
                        'delta': round(call_delta, 4),
                        'gamma': round(call_gamma, 6),
                        'theta': round(call_theta, 4),
                        'vega': round(call_vega, 4),
                        'intrinsic_value': round(max(0, self.spot_price - strike), 2),
                        'time_value': round(max(0, call_price - max(0, self.spot_price - strike)), 2)
                    },
                    'put': {
                        'symbol': strike_data.get('putSymbol', f'{self.symbol}P{strike}'),
                        'ltp': round(put_price, 2),
                        'bid': strike_data.get('putBid', 0),
                        'ask': strike_data.get('putAsk', 0),
                        'bid_qty': strike_data.get('putBidQty', 0),
                        'ask_qty': strike_data.get('putAskQty', 0),
                        'volume': strike_data.get('putVolume', 0),
                        'oi': strike_data.get('putOI', 0),
                        'iv': round(strike_data.get('putIV', 0.25), 4),
                        'delta': round(put_delta, 4),
                        'gamma': round(call_gamma, 6),
                        'theta': round(put_theta, 4),
                        'vega': round(call_vega, 4),
                        'intrinsic_value': round(max(0, strike - self.spot_price), 2),
                        'time_value': round(max(0, put_price - max(0, strike - self.spot_price)), 2)
                    },
                    'oi_change': strike_data.get('callOI', 0) + strike_data.get('putOI', 0)
                }

                parsed_chain['strikes'].append(strike_entry)

            self.chain_data = parsed_chain
            logger.info(f"✅ Options chain parsed: {self.symbol} | {len(strike_details)} strikes")
            return parsed_chain

        except Exception as e:
            logger.error(f"❌ Error parsing options chain: {str(e)}")
            return {'error': str(e)}

    def calculate_pcr(self) -> Dict:
        """Calculate Put/Call Ratio"""
        try:
            total_put_oi = sum(s['put']['oi'] for s in self.chain_data.get('strikes', []))
            total_call_oi = sum(s['call']['oi'] for s in self.chain_data.get('strikes', []))

            if total_call_oi == 0:
                return {'pcr': 0, 'signal': 'NEUTRAL'}

            pcr = total_put_oi / total_call_oi

            if pcr < 0.7:
                signal = 'BULLISH'
            elif pcr > 1.3:
                signal = 'BEARISH'
            else:
                signal = 'NEUTRAL'

            logger.info(f"📊 PCR Calculated: {pcr:.2f} | Signal: {signal}")
            return {
                'pcr': round(pcr, 2),
                'put_oi': total_put_oi,
                'call_oi': total_call_oi,
                'signal': signal
            }

        except Exception as e:
            logger.error(f"❌ Error calculating PCR: {str(e)}")
            return {'pcr': 0, 'signal': 'ERROR'}

    def calculate_max_pain(self) -> Dict:
        """Calculate Max Pain (price where max number of options expire worthless)"""
        try:
            strikes = sorted([s['strike'] for s in self.chain_data.get('strikes', [])])
            if not strikes:
                return {'max_pain': self.spot_price, 'bias': 'NEUTRAL'}

            # Simplified calculation: weighted average of OI
            total_oi = sum(s['call']['oi'] + s['put']['oi'] for s in self.chain_data.get('strikes', []))
            max_pain = sum(
                s['strike'] * (s['call']['oi'] + s['put']['oi'])
                for s in self.chain_data.get('strikes', [])
            ) / total_oi

            if max_pain > self.spot_price:
                bias = 'UPSIDE'
            elif max_pain < self.spot_price:
                bias = 'DOWNSIDE'
            else:
                bias = 'AT_SPOT'

            logger.info(f"📍 Max Pain: {max_pain:.2f} | Bias: {bias}")
            return {
                'max_pain': round(max_pain, 2),
                'distance_from_spot': round(max_pain - self.spot_price, 2),
                'bias': bias
            }

        except Exception as e:
            logger.error(f"❌ Error calculating max pain: {str(e)}")
            return {'max_pain': self.spot_price, 'bias': 'ERROR'}

    def analyze_oi_buildup(self, previous_chain: Dict = None) -> Dict:
        """Analyze OI buildup direction (calls vs puts)"""
        try:
            total_call_oi = sum(s['call']['oi'] for s in self.chain_data.get('strikes', []))
            total_put_oi = sum(s['put']['oi'] for s in self.chain_data.get('strikes', []))

            if previous_chain:
                prev_call_oi = sum(s['call']['oi'] for s in previous_chain.get('strikes', []))
                prev_put_oi = sum(s['put']['oi'] for s in previous_chain.get('strikes', []))

                call_change_pct = ((total_call_oi - prev_call_oi) / prev_call_oi * 100) if prev_call_oi > 0 else 0
                put_change_pct = ((total_put_oi - prev_put_oi) / prev_put_oi * 100) if prev_put_oi > 0 else 0
            else:
                call_change_pct = 0
                put_change_pct = 0

            if call_change_pct > 5:
                direction = 'CALL_OI_BUILDUP'
            elif put_change_pct > 5:
                direction = 'PUT_OI_BUILDUP'
            elif call_change_pct < -5 and put_change_pct < -5:
                direction = 'OI_UNWINDING'
            else:
                direction = 'STABLE'

            logger.info(
                f"📈 OI Buildup: {direction} | "
                f"Call OI: {call_change_pct:+.1f}% | Put OI: {put_change_pct:+.1f}%"
            )

            return {
                'direction': direction,
                'call_oi_change_pct': round(call_change_pct, 2),
                'put_oi_change_pct': round(put_change_pct, 2),
                'total_call_oi': total_call_oi,
                'total_put_oi': total_put_oi
            }

        except Exception as e:
            logger.error(f"❌ Error analyzing OI buildup: {str(e)}")
            return {'direction': 'ERROR'}

    def get_atm_options(self, width: float = 2) -> Dict:
        """Get ATM and nearby options strikes"""
        try:
            atm_strikes = [
                s for s in self.chain_data.get('strikes', [])
                if abs(s['atm_distance_pct']) <= width
            ]

            if not atm_strikes:
                return {'error': 'No ATM strikes found'}

            atm_strikes_sorted = sorted(atm_strikes, key=lambda x: abs(x['atm_distance']))

            return {
                'atm_strike': atm_strikes_sorted[0]['strike'],
                'nearby_strikes': [s['strike'] for s in atm_strikes_sorted[:5]],
                'options': atm_strikes_sorted
            }

        except Exception as e:
            logger.error(f"❌ Error getting ATM options: {str(e)}")
            return {'error': str(e)}

    def get_chain_summary(self) -> Dict:
        """Get comprehensive options chain summary"""
        try:
            pcr_data = self.calculate_pcr()
            max_pain_data = self.calculate_max_pain()
            oi_buildup_data = self.analyze_oi_buildup()
            atm_data = self.get_atm_options()

            total_volume = sum(
                s['call']['volume'] + s['put']['volume']
                for s in self.chain_data.get('strikes', [])
            )

            summary = {
                'symbol': self.symbol,
                'spot_price': self.spot_price,
                'expiry_days': self.expiry_days,
                'timestamp': datetime.now().isoformat(),
                'pcr': pcr_data,
                'max_pain': max_pain_data,
                'oi_buildup': oi_buildup_data,
                'total_volume': total_volume,
                'atm_options': atm_data,
                'total_strikes': len(self.chain_data.get('strikes', []))
            }

            logger.info(f"✅ Chain summary generated for {self.symbol}")
            return summary

        except Exception as e:
            logger.error(f"❌ Error generating chain summary: {str(e)}")
            return {'error': str(e)}

    def export_chain_data(self, format: str = 'json') -> str:
        """Export parsed chain data"""
        import json
        try:
            if format == 'json':
                return json.dumps(self.chain_data, indent=2)
            else:
                return str(self.chain_data)
        except Exception as e:
            logger.error(f"❌ Error exporting chain data: {str(e)}")
            return ''
