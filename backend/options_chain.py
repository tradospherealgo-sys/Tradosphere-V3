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

    @staticmethod
    def calculate_rho(S, K, T, r, sigma, option_type='CALL'):
        """Calculate rho (sensitivity to interest rate change per 1%)"""
        if T <= 0 or sigma <= 0:
            return 0.0

        d1, d2 = GreeksCalculator.calculate_d1_d2(S, K, T, r, sigma)

        if option_type == 'CALL':
            rho = K * T * np.exp(-r * T) * GreeksCalculator.normal_cdf(d2) / 100.0
        else:
            rho = -K * T * np.exp(-r * T) * GreeksCalculator.normal_cdf(-d2) / 100.0

        return rho

    @staticmethod
    def calculate_expected_move(S, T, sigma):
        """Calculate expected move (1 standard deviation move in $ and %)"""
        dollar_move = S * sigma * np.sqrt(T)
        percent_move = (dollar_move / S) * 100.0
        return {
            'dollar_move': dollar_move,
            'percent_move': percent_move,
            'support': S - dollar_move,
            'resistance': S + dollar_move
        }


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

    # FEATURE #1: IV Rank/Percentile
    def calculate_iv_rank_percentile(self, historical_iv_data: List[float] = None, current_iv: float = None) -> Dict:
        """
        Calculate IV Rank and IV Percentile

        IV Rank: (Current IV - 52-week Low IV) / (52-week High IV - 52-week Low IV)
        IV Percentile: % of days in past year when IV was below current IV

        Args:
            historical_iv_data: List of historical IV values (last 252 trading days)
            current_iv: Current IV (if not provided, will get from ATM strike)
        """
        try:
            # Get current IV (ATM call IV or provided)
            if current_iv is None:
                strikes = self.chain_data.get('strikes', [])
                if not strikes:
                    current_iv = 0.25
                else:
                    atm_strike = min(strikes, key=lambda x: abs(x['atm_distance']))
                    current_iv = atm_strike['call']['iv'] / 100.0 if 'call' in atm_strike else 0.25
            else:
                current_iv = current_iv / 100.0 if current_iv > 1 else current_iv  # Handle percentage input

            if not historical_iv_data or len(historical_iv_data) == 0:
                logger.warning("⚠️ No historical IV data provided")
                return {
                    'current_iv': round(current_iv * 100, 2),
                    'iv_rank': 'N/A',
                    'iv_percentile': 'N/A',
                    'iv_52w_high': 'N/A',
                    'iv_52w_low': 'N/A'
                }

            # Calculate IV Rank
            iv_52w_high = max(historical_iv_data)
            iv_52w_low = min(historical_iv_data)
            iv_range = iv_52w_high - iv_52w_low

            if iv_range == 0:
                iv_rank = 50
            else:
                iv_rank = ((current_iv - iv_52w_low) / iv_range) * 100

            # Calculate IV Percentile
            below_current = sum(1 for iv in historical_iv_data if iv <= current_iv)
            iv_percentile = (below_current / len(historical_iv_data)) * 100

            logger.info(
                f"📊 IV Analysis: Rank={iv_rank:.1f}% | Percentile={iv_percentile:.1f}% | "
                f"Current={current_iv*100:.2f}% | Range=[{iv_52w_low*100:.2f}%-{iv_52w_high*100:.2f}%]"
            )

            return {
                'current_iv': round(current_iv * 100, 2),
                'iv_rank': round(iv_rank, 2),
                'iv_percentile': round(iv_percentile, 2),
                'iv_52w_high': round(iv_52w_high * 100, 2),
                'iv_52w_low': round(iv_52w_low * 100, 2),
                'iv_range': round(iv_range * 100, 2),
                'iv_signal': 'HIGH' if iv_rank > 75 else ('LOW' if iv_rank < 25 else 'MEDIUM')
            }

        except Exception as e:
            logger.error(f"❌ Error calculating IV rank/percentile: {str(e)}")
            return {'error': str(e)}

    # FEATURE #2: Rho (Interest Rate Sensitivity)
    def calculate_rho_for_chain(self) -> Dict:
        """Calculate rho for ATM and nearby options"""
        try:
            atm_options = self.get_atm_options(width=3)
            if 'error' in atm_options:
                return atm_options

            rho_data = {
                'atm_strike': atm_options['atm_strike'],
                'options': []
            }

            for strike_data in atm_options['options'][:5]:  # Top 5 ATM strikes
                strike = strike_data['strike']
                call_iv = strike_data['call']['iv'] / 100.0
                put_iv = strike_data['put']['iv'] / 100.0

                call_rho = self.greeks_calc.calculate_rho(self.spot_price, strike, self.time_to_expiry,
                                                         self.risk_free_rate, call_iv, 'CALL')
                put_rho = self.greeks_calc.calculate_rho(self.spot_price, strike, self.time_to_expiry,
                                                        self.risk_free_rate, put_iv, 'PUT')

                rho_data['options'].append({
                    'strike': strike,
                    'call_rho': round(call_rho, 4),
                    'put_rho': round(put_rho, 4)
                })

            logger.info(f"✅ Rho calculated for {len(rho_data['options'])} strikes")
            return rho_data

        except Exception as e:
            logger.error(f"❌ Error calculating rho: {str(e)}")
            return {'error': str(e)}

    # FEATURE #3: Expected Move
    def calculate_expected_move_for_stock(self) -> Dict:
        """Calculate expected move (1 std dev) for the underlying"""
        try:
            atm_strike = min(self.chain_data.get('strikes', []),
                           key=lambda x: abs(x['atm_distance']))
            current_iv = atm_strike['call']['iv'] / 100.0

            expected_move = self.greeks_calc.calculate_expected_move(self.spot_price,
                                                                    self.time_to_expiry, current_iv)

            logger.info(
                f"📊 Expected Move (1 STD): ${expected_move['dollar_move']:.2f} | "
                f"{expected_move['percent_move']:.2f}% | "
                f"Support: {expected_move['support']:.2f} | Resistance: {expected_move['resistance']:.2f}"
            )

            return {
                'spot': self.spot_price,
                'expected_move_dollar': round(expected_move['dollar_move'], 2),
                'expected_move_percent': round(expected_move['percent_move'], 2),
                'support_1std': round(expected_move['support'], 2),
                'resistance_1std': round(expected_move['resistance'], 2),
                'days_to_expiry': self.expiry_days
            }

        except Exception as e:
            logger.error(f"❌ Error calculating expected move: {str(e)}")
            return {'error': str(e)}

    # FEATURE #4: Greeks Aggregation (Portfolio Greeks)
    def calculate_portfolio_greeks(self, positions: List[Dict]) -> Dict:
        """
        Calculate aggregate Greeks for a portfolio of options positions

        Args:
            positions: [
                {'strike': 23000, 'type': 'CALL', 'quantity': 2, 'price': 450},
                {'strike': 23500, 'type': 'PUT', 'quantity': -1, 'price': 42}
            ]
        """
        try:
            total_delta = 0
            total_gamma = 0
            total_theta = 0
            total_vega = 0
            total_cost = 0

            for pos in positions:
                strike = pos['strike']
                option_type = pos['type']
                quantity = pos['quantity']
                price = pos.get('price', 0)

                # Find strike in chain data
                strike_data = next((s for s in self.chain_data.get('strikes', [])
                                  if s['strike'] == strike), None)
                if not strike_data:
                    continue

                greeks = strike_data[option_type.lower()]
                total_delta += greeks['delta'] * quantity * 100  # Per contract
                total_gamma += greeks['gamma'] * quantity * 100
                total_theta += greeks['theta'] * quantity
                total_vega += greeks['vega'] * quantity

                total_cost += price * quantity * 100  # Assuming 100 shares per contract

            logger.info(
                f"📊 Portfolio Greeks: Delta={total_delta:.2f} | Gamma={total_gamma:.4f} | "
                f"Theta={total_theta:.2f} | Vega={total_vega:.2f}"
            )

            return {
                'total_delta': round(total_delta, 2),
                'total_gamma': round(total_gamma, 4),
                'total_theta': round(total_theta, 2),
                'total_vega': round(total_vega, 2),
                'total_notional_cost': round(total_cost, 2),
                'positions': len(positions)
            }

        except Exception as e:
            logger.error(f"❌ Error calculating portfolio Greeks: {str(e)}")
            return {'error': str(e)}

    # FEATURE #5: Skew Analysis
    def analyze_skew(self) -> Dict:
        """
        Analyze IV skew (IV differences across strikes)
        Skew = Call IV - Put IV at same strike
        """
        try:
            skew_data = {
                'atm_strike': None,
                'skew_values': [],
                'skew_direction': None,
                'skew_intensity': None
            }

            skews = []
            atm_distance = float('inf')
            atm_strike = None

            for strike_data in self.chain_data.get('strikes', []):
                call_iv = strike_data['call']['iv']
                put_iv = strike_data['put']['iv']
                skew = call_iv - put_iv

                skews.append(skew)
                skew_data['skew_values'].append({
                    'strike': strike_data['strike'],
                    'call_iv': call_iv,
                    'put_iv': put_iv,
                    'skew': round(skew, 2)
                })

                # Find ATM
                if abs(strike_data['atm_distance']) < atm_distance:
                    atm_distance = abs(strike_data['atm_distance'])
                    atm_strike = strike_data['strike']

            skew_data['atm_strike'] = atm_strike
            avg_skew = np.mean(skews) if skews else 0

            if avg_skew > 0.5:
                skew_data['skew_direction'] = 'CALL_SKEW'
                skew_data['skew_intensity'] = 'HIGH' if avg_skew > 1.5 else 'MEDIUM'
            elif avg_skew < -0.5:
                skew_data['skew_direction'] = 'PUT_SKEW'
                skew_data['skew_intensity'] = 'HIGH' if avg_skew < -1.5 else 'MEDIUM'
            else:
                skew_data['skew_direction'] = 'BALANCED'
                skew_data['skew_intensity'] = 'LOW'

            logger.info(f"📊 IV Skew: {skew_data['skew_direction']} ({skew_data['skew_intensity']}) | Avg Skew: {avg_skew:.2f}")
            return skew_data

        except Exception as e:
            logger.error(f"❌ Error analyzing skew: {str(e)}")
            return {'error': str(e)}

    # FEATURE #6: PCR/Max Pain/OI Buildup Integration
    def get_comprehensive_oi_analysis(self, previous_chain: Dict = None) -> Dict:
        """Integrated PCR, Max Pain, and OI Buildup analysis"""
        try:
            pcr_data = self.calculate_pcr()
            max_pain_data = self.calculate_max_pain()
            oi_buildup_data = self.analyze_oi_buildup(previous_chain)

            return {
                'pcr': pcr_data,
                'max_pain': max_pain_data,
                'oi_buildup': oi_buildup_data,
                'analysis': {
                    'bias': self._determine_oi_bias(pcr_data, max_pain_data, oi_buildup_data),
                    'strength': self._determine_bias_strength(oi_buildup_data)
                }
            }

        except Exception as e:
            logger.error(f"❌ Error in OI analysis: {str(e)}")
            return {'error': str(e)}

    def _determine_oi_bias(self, pcr, max_pain, oi_buildup) -> str:
        """Determine overall bias from OI metrics"""
        if pcr.get('signal') == 'BULLISH' and max_pain.get('bias') == 'UPSIDE' and \
           oi_buildup.get('direction') == 'CALL_OI_BUILDUP':
            return 'STRONG_BULLISH'
        elif pcr.get('signal') == 'BEARISH' and max_pain.get('bias') == 'DOWNSIDE' and \
             oi_buildup.get('direction') == 'PUT_OI_BUILDUP':
            return 'STRONG_BEARISH'
        elif pcr.get('signal') == 'BULLISH' or max_pain.get('bias') == 'UPSIDE':
            return 'BULLISH'
        elif pcr.get('signal') == 'BEARISH' or max_pain.get('bias') == 'DOWNSIDE':
            return 'BEARISH'
        else:
            return 'NEUTRAL'

    def _determine_bias_strength(self, oi_buildup) -> str:
        """Determine strength of bias from OI changes"""
        change = max(abs(oi_buildup.get('call_oi_change_pct', 0)),
                    abs(oi_buildup.get('put_oi_change_pct', 0)))
        if change > 15:
            return 'VERY_HIGH'
        elif change > 10:
            return 'HIGH'
        elif change > 5:
            return 'MEDIUM'
        else:
            return 'LOW'

    # FEATURE #7: Lot Size Handling
    def set_lot_size(self, lot_size: int):
        """
        Set lot size for the underlying
        NIFTY50: 75, BANKNIFTY: 40, Stocks: 1, etc.
        """
        self.lot_size = lot_size
        logger.info(f"✅ Lot size set to {lot_size} for {self.symbol}")

    def get_greeks_with_lot_size(self, strike: int, option_type: str) -> Dict:
        """Get Greeks adjusted for lot size"""
        try:
            strike_data = next((s for s in self.chain_data.get('strikes', [])
                              if s['strike'] == strike), None)
            if not strike_data:
                return {'error': f'Strike {strike} not found'}

            option_data = strike_data.get(option_type.lower())
            if not option_data:
                return {'error': f'Option type {option_type} not found'}

            lot_size = getattr(self, 'lot_size', 1)

            return {
                'strike': strike,
                'type': option_type,
                'lot_size': lot_size,
                'delta_per_lot': round(option_data['delta'] * lot_size, 2),
                'gamma_per_lot': round(option_data['gamma'] * lot_size, 6),
                'theta_per_lot': round(option_data['theta'] * lot_size / 100, 2),
                'vega_per_lot': round(option_data['vega'] * lot_size / 100, 2)
            }

        except Exception as e:
            logger.error(f"❌ Error getting Greeks with lot size: {str(e)}")
            return {'error': str(e)}

    # FEATURE #8: Historical OI Tracking
    def track_oi_history(self, timestamp: str = None):
        """
        Store current chain data as historical snapshot for OI tracking
        Call this periodically to build OI history
        """
        try:
            if not hasattr(self, 'oi_history'):
                self.oi_history = []

            timestamp = timestamp or datetime.now().isoformat()

            snapshot = {
                'timestamp': timestamp,
                'spot': self.spot_price,
                'strikes': []
            }

            for strike_data in self.chain_data.get('strikes', []):
                snapshot['strikes'].append({
                    'strike': strike_data['strike'],
                    'call_oi': strike_data['call']['oi'],
                    'put_oi': strike_data['put']['oi'],
                    'total_oi': strike_data['total_oi'],
                    'call_iv': strike_data['call']['iv'],
                    'put_iv': strike_data['put']['iv']
                })

            self.oi_history.append(snapshot)
            logger.info(f"✅ OI snapshot captured at {timestamp}")
            return {'status': 'success', 'snapshots': len(self.oi_history)}

        except Exception as e:
            logger.error(f"❌ Error tracking OI history: {str(e)}")
            return {'error': str(e)}

    def get_oi_change_from_history(self, strikes: List[int] = None) -> Dict:
        """Analyze OI changes from historical data"""
        try:
            if not hasattr(self, 'oi_history') or len(self.oi_history) < 2:
                return {'error': 'Insufficient history (need 2+ snapshots)'}

            current = self.oi_history[-1]
            previous = self.oi_history[-2]

            analysis = {'snapshots': len(self.oi_history), 'oi_changes': []}

            for curr_strike in current['strikes']:
                if strikes and curr_strike['strike'] not in strikes:
                    continue

                prev_strike = next((s for s in previous['strikes']
                                  if s['strike'] == curr_strike['strike']), None)
                if not prev_strike:
                    continue

                call_oi_change = curr_strike['call_oi'] - prev_strike['call_oi']
                put_oi_change = curr_strike['put_oi'] - prev_strike['put_oi']
                call_oi_change_pct = (call_oi_change / prev_strike['call_oi'] * 100) if prev_strike['call_oi'] > 0 else 0
                put_oi_change_pct = (put_oi_change / prev_strike['put_oi'] * 100) if prev_strike['put_oi'] > 0 else 0

                analysis['oi_changes'].append({
                    'strike': curr_strike['strike'],
                    'call_oi_change': call_oi_change,
                    'call_oi_change_pct': round(call_oi_change_pct, 2),
                    'put_oi_change': put_oi_change,
                    'put_oi_change_pct': round(put_oi_change_pct, 2)
                })

            logger.info(f"✅ OI changes analyzed for {len(analysis['oi_changes'])} strikes")
            return analysis

        except Exception as e:
            logger.error(f"❌ Error analyzing OI changes: {str(e)}")
            return {'error': str(e)}

    # FEATURE #9: Greeks Ladder (Real-time Greeks over time)
    def build_greeks_ladder(self, strikes: List[int] = None) -> Dict:
        """
        Build Greeks ladder showing Greeks progression across strikes
        Useful for visualizing risk exposure
        """
        try:
            ladder = {
                'symbol': self.symbol,
                'spot': self.spot_price,
                'expiry_days': self.expiry_days,
                'ladder': []
            }

            for strike_data in self.chain_data.get('strikes', []):
                if strikes and strike_data['strike'] not in strikes:
                    continue

                ladder['ladder'].append({
                    'strike': strike_data['strike'],
                    'distance_pct': strike_data['atm_distance_pct'],
                    'call': {
                        'price': strike_data['call']['ltp'],
                        'delta': strike_data['call']['delta'],
                        'gamma': strike_data['call']['gamma'],
                        'theta': strike_data['call']['theta'],
                        'vega': strike_data['call']['vega'],
                        'oi': strike_data['call']['oi']
                    },
                    'put': {
                        'price': strike_data['put']['ltp'],
                        'delta': strike_data['put']['delta'],
                        'gamma': strike_data['put']['gamma'],
                        'theta': strike_data['put']['theta'],
                        'vega': strike_data['put']['vega'],
                        'oi': strike_data['put']['oi']
                    }
                })

            logger.info(f"✅ Greeks ladder built with {len(ladder['ladder'])} strikes")
            return ladder

        except Exception as e:
            logger.error(f"❌ Error building Greeks ladder: {str(e)}")
            return {'error': str(e)}
