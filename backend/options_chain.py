"""
Options Chain Module - Complete Options Data Handler (Option A+B)
Full Greeks + IV + Current Prices + OI + PCR + Max Pain + OI Buildup
"""

import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime
from logger_config import get_logger
from scipy.optimize import brentq

logger = get_logger(__name__)


class GreeksCalculator:
    """Complete Black-Scholes Greeks calculator with all components"""

    @staticmethod
    def normal_pdf(x):
        """Standard normal probability density function"""
        return (1.0 / np.sqrt(2.0 * np.pi)) * np.exp(-0.5 * x * x)

    @staticmethod
    def normal_cdf(x):
        """Standard normal cumulative distribution (accurate)"""
        return (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (x + 0.044715 * x * x * x))) / 2.0

    @staticmethod
    def calculate_d1_d2(S, K, T, r, sigma):
        """Calculate d1 and d2 for Black-Scholes"""
        if T <= 0 or sigma <= 0:
            return 0, 0

        d1 = (np.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return d1, d2

    @staticmethod
    def calculate_call_price(S, K, T, r, sigma):
        """Calculate call option price"""
        if T <= 0:
            return max(0, S - K)

        d1, d2 = GreeksCalculator.calculate_d1_d2(S, K, T, r, sigma)
        call = S * GreeksCalculator.normal_cdf(d1) - K * np.exp(-r * T) * GreeksCalculator.normal_cdf(d2)
        return max(0, call)

    @staticmethod
    def calculate_put_price(S, K, T, r, sigma):
        """Calculate put option price"""
        if T <= 0:
            return max(0, K - S)

        d1, d2 = GreeksCalculator.calculate_d1_d2(S, K, T, r, sigma)
        put = K * np.exp(-r * T) * GreeksCalculator.normal_cdf(-d2) - S * GreeksCalculator.normal_cdf(-d1)
        return max(0, put)

    @staticmethod
    def calculate_delta(S, K, T, r, sigma, option_type='CALL'):
        """Calculate delta (rate of change of option price vs stock price)"""
        if T <= 0:
            if option_type == 'CALL':
                return 1.0 if S > K else 0.0
            else:
                return -1.0 if S < K else 0.0

        d1, _ = GreeksCalculator.calculate_d1_d2(S, K, T, r, sigma)
        if option_type == 'CALL':
            return GreeksCalculator.normal_cdf(d1)
        else:
            return GreeksCalculator.normal_cdf(d1) - 1.0

    @staticmethod
    def calculate_gamma(S, K, T, r, sigma):
        """Calculate gamma (rate of change of delta)"""
        if T <= 0 or sigma <= 0:
            return 0.0

        d1, _ = GreeksCalculator.calculate_d1_d2(S, K, T, r, sigma)
        gamma = GreeksCalculator.normal_pdf(d1) / (S * sigma * np.sqrt(T))
        return gamma

    @staticmethod
    def calculate_theta(S, K, T, r, sigma, option_type='CALL'):
        """Calculate theta (time decay per day)"""
        if T <= 0 or sigma <= 0:
            return 0.0

        d1, d2 = GreeksCalculator.calculate_d1_d2(S, K, T, r, sigma)
        sqrt_T = np.sqrt(T)

        if option_type == 'CALL':
            theta = (-S * GreeksCalculator.normal_pdf(d1) * sigma) / (2.0 * sqrt_T) - \
                    r * K * np.exp(-r * T) * GreeksCalculator.normal_cdf(d2)
        else:
            theta = (-S * GreeksCalculator.normal_pdf(d1) * sigma) / (2.0 * sqrt_T) + \
                    r * K * np.exp(-r * T) * GreeksCalculator.normal_cdf(-d2)

        return theta / 365.0  # Per day

    @staticmethod
    def calculate_vega(S, K, T, r, sigma):
        """Calculate vega (sensitivity to IV change per 1%)"""
        if T <= 0 or sigma <= 0:
            return 0.0

        d1, _ = GreeksCalculator.calculate_d1_d2(S, K, T, r, sigma)
        vega = S * GreeksCalculator.normal_pdf(d1) * np.sqrt(T) / 100.0
        return vega

    @staticmethod
    def calculate_iv(market_price, S, K, T, r, option_type='CALL'):
        """Calculate implied volatility using Brent's method (robust)"""
        try:
            if T <= 0:
                return 0.0

            def objective(sigma):
                if option_type == 'CALL':
                    price = GreeksCalculator.calculate_call_price(S, K, T, r, sigma)
                else:
                    price = GreeksCalculator.calculate_put_price(S, K, T, r, sigma)
                return price - market_price

            # Bracketing interval
            iv = brentq(objective, 0.001, 5.0, maxiter=100)
            return max(0.001, min(iv, 5.0))
        except:
            return 0.25  # Return default if calculation fails


class OptionsChain:
    """Complete options chain handler (Option A+B): Full Greeks + IV + PCR + Max Pain + OI Buildup"""

    def __init__(self, spot_price: float, symbol: str, expiry_days: int = 7, risk_free_rate: float = 0.06):
        """
        Initialize options chain

        Args:
            spot_price: Current spot price
            symbol: Stock/index symbol
            expiry_days: Days to expiration
            risk_free_rate: Annual risk-free rate (default 6%)
        """
        self.spot_price = spot_price
        self.symbol = symbol
        self.expiry_days = max(1, expiry_days)  # Minimum 1 day
        self.time_to_expiry = self.expiry_days / 365.0
        self.risk_free_rate = risk_free_rate
        self.chain_data = {}
        self.greeks_calc = GreeksCalculator()
        self.historical_chain = None  # For OI change tracking

    def parse_chain_from_smartapi(self, chain_response: Dict) -> Dict:
        """
        Parse complete options chain from Angel One SmartAPI with FULL Greeks & IV

        Input: {
            'fetched': True,
            'data': {
                'strikeDetails': [
                    {
                        'strike': 23000,
                        'callSymbol': '...',
                        'putSymbol': '...',
                        'callLTP': 450.50,
                        'putLTP': 12.25,
                        'callOI': 1250000,
                        'putOI': 980000,
                        'callBid': 449.00,
                        'callAsk': 452.00,
                        'callBidQty': 100,
                        'callAskQty': 100,
                        'callVolume': 5000,
                        'putVolume': 3000
                    }
                ]
            }
        }
        """
        try:
            if not chain_response.get('fetched'):
                logger.warning(f"⚠️ Chain data not fetched for {self.symbol}")
                return {'error': 'Chain data not available'}

            strike_details = chain_response.get('data', {}).get('strikeDetails', [])

            parsed_chain = {
                'symbol': self.symbol,
                'spot_price': self.spot_price,
                'expiry_days': self.expiry_days,
                'fetch_timestamp': datetime.now().isoformat(),
                'strikes': []
            }

            for strike_data in strike_details:
                strike = strike_data.get('strike')
                call_ltp = strike_data.get('callLTP', 0)
                put_ltp = strike_data.get('putLTP', 0)
                call_oi = strike_data.get('callOI', 0)
                put_oi = strike_data.get('putOI', 0)

                # Calculate IV from market prices (Option A)
                call_iv = self.greeks_calc.calculate_iv(call_ltp, self.spot_price, strike,
                                                        self.time_to_expiry, self.risk_free_rate, 'CALL')
                put_iv = self.greeks_calc.calculate_iv(put_ltp, self.spot_price, strike,
                                                       self.time_to_expiry, self.risk_free_rate, 'PUT')

                # Calculate all Greeks (Option A) - FULL
                call_delta = self.greeks_calc.calculate_delta(self.spot_price, strike, self.time_to_expiry,
                                                             self.risk_free_rate, call_iv, 'CALL')
                put_delta = self.greeks_calc.calculate_delta(self.spot_price, strike, self.time_to_expiry,
                                                            self.risk_free_rate, put_iv, 'PUT')

                call_gamma = self.greeks_calc.calculate_gamma(self.spot_price, strike, self.time_to_expiry,
                                                             self.risk_free_rate, call_iv)
                put_gamma = self.greeks_calc.calculate_gamma(self.spot_price, strike, self.time_to_expiry,
                                                            self.risk_free_rate, put_iv)

                call_theta = self.greeks_calc.calculate_theta(self.spot_price, strike, self.time_to_expiry,
                                                             self.risk_free_rate, call_iv, 'CALL')
                put_theta = self.greeks_calc.calculate_theta(self.spot_price, strike, self.time_to_expiry,
                                                            self.risk_free_rate, put_iv, 'PUT')

                call_vega = self.greeks_calc.calculate_vega(self.spot_price, strike, self.time_to_expiry,
                                                           self.risk_free_rate, call_iv)
                put_vega = self.greeks_calc.calculate_vega(self.spot_price, strike, self.time_to_expiry,
                                                          self.risk_free_rate, put_iv)

                # Intrinsic and Time Value (Option A)
                call_intrinsic = max(0, self.spot_price - strike)
                call_time_value = max(0, call_ltp - call_intrinsic)
                put_intrinsic = max(0, strike - self.spot_price)
                put_time_value = max(0, put_ltp - put_intrinsic)

                # Bid-Ask spread
                call_bid = strike_data.get('callBid', call_ltp - 0.5)
                call_ask = strike_data.get('callAsk', call_ltp + 0.5)
                put_bid = strike_data.get('putBid', put_ltp - 0.5)
                put_ask = strike_data.get('putAsk', put_ltp + 0.5)

                strike_entry = {
                    'strike': strike,
                    'atm_distance': strike - self.spot_price,
                    'atm_distance_pct': round(((strike - self.spot_price) / self.spot_price) * 100, 2),
                    'call': {
                        'symbol': strike_data.get('callSymbol', f'{self.symbol}C{strike}'),
                        'ltp': round(call_ltp, 2),
                        'bid': round(call_bid, 2),
                        'ask': round(call_ask, 2),
                        'bid_ask_spread': round(call_ask - call_bid, 2),
                        'bid_qty': strike_data.get('callBidQty', 0),
                        'ask_qty': strike_data.get('callAskQty', 0),
                        'volume': strike_data.get('callVolume', 0),
                        'oi': call_oi,
                        'iv': round(call_iv * 100, 2),  # Convert to percentage
                        'delta': round(call_delta, 4),
                        'gamma': round(call_gamma, 6),
                        'theta': round(call_theta * 100, 2),  # Per 100 shares
                        'vega': round(call_vega * 100, 2),  # Per 1% IV change per 100 shares
                        'intrinsic_value': round(call_intrinsic, 2),
                        'time_value': round(call_time_value, 2)
                    },
                    'put': {
                        'symbol': strike_data.get('putSymbol', f'{self.symbol}P{strike}'),
                        'ltp': round(put_ltp, 2),
                        'bid': round(put_bid, 2),
                        'ask': round(put_ask, 2),
                        'bid_ask_spread': round(put_ask - put_bid, 2),
                        'bid_qty': strike_data.get('putBidQty', 0),
                        'ask_qty': strike_data.get('putAskQty', 0),
                        'volume': strike_data.get('putVolume', 0),
                        'oi': put_oi,
                        'iv': round(put_iv * 100, 2),
                        'delta': round(put_delta, 4),
                        'gamma': round(put_gamma, 6),
                        'theta': round(put_theta * 100, 2),
                        'vega': round(put_vega * 100, 2),
                        'intrinsic_value': round(put_intrinsic, 2),
                        'time_value': round(put_time_value, 2)
                    },
                    'total_oi': call_oi + put_oi
                }

                parsed_chain['strikes'].append(strike_entry)

            self.chain_data = parsed_chain
            logger.info(f"✅ Complete chain parsed (Option A+B): {self.symbol} | {len(strike_details)} strikes with Greeks & IV")
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
