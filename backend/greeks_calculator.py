"""
Greeks Calculator - Options Analytics
Calculates Delta, Gamma, Vega, Theta, Rho using Black-Scholes model
"""

import math
from typing import Dict, List
from scipy.stats import norm


class GreeksInjector:
    """Injects Black-Scholes Greeks into option strike data"""

    # Constants
    RISK_FREE_RATE = 0.06  # 6% annual risk-free rate
    IMPLIED_VOLATILITY = 0.25  # 25% implied volatility

    @staticmethod
    def inject_greeks_into_strikes(strikes: List[Dict], spot_price: float,
                                  atm_call_ltp: float, atm_put_ltp: float,
                                  days_to_expiry: int = 1) -> List[Dict]:
        """
        Inject Greeks into strike data

        Args:
            strikes: List of strike data with CE/PE information
            spot_price: Current spot price
            atm_call_ltp: ATM call last traded price
            atm_put_ltp: ATM put last traded price
            days_to_expiry: Days to expiration (default 1)

        Returns:
            List of strikes with Greeks injected
        """
        time_to_expiry = max(days_to_expiry, 1) / 365.0  # Convert days to years

        for strike in strikes:
            strike_price = float(strike.get('strike', 0))

            # Calculate Greeks for Call option
            try:
                call_data = strike.get('ce', {})
                if call_data:
                    call_ltp = float(call_data.get('ltp', atm_call_ltp))
                    call_iv = GreeksInjector._calculate_iv(spot_price, strike_price, call_ltp,
                                                           time_to_expiry, is_call=True)

                    call_greeks = GreeksInjector._calculate_greeks(
                        spot_price, strike_price, time_to_expiry,
                        call_iv, option_type='call'
                    )

                    strike['ce']['delta'] = round(call_greeks['delta'], 4)
                    strike['ce']['gamma'] = round(call_greeks['gamma'], 4)
                    strike['ce']['vega'] = round(call_greeks['vega'], 4)
                    strike['ce']['theta'] = round(call_greeks['theta'], 4)
                    strike['ce']['rho'] = round(call_greeks['rho'], 4)
            except Exception as e:
                pass

            # Calculate Greeks for Put option
            try:
                put_data = strike.get('pe', {})
                if put_data:
                    put_ltp = float(put_data.get('ltp', atm_put_ltp))
                    put_iv = GreeksInjector._calculate_iv(spot_price, strike_price, put_ltp,
                                                          time_to_expiry, is_call=False)

                    put_greeks = GreeksInjector._calculate_greeks(
                        spot_price, strike_price, time_to_expiry,
                        put_iv, option_type='put'
                    )

                    strike['pe']['delta'] = round(put_greeks['delta'], 4)
                    strike['pe']['gamma'] = round(put_greeks['gamma'], 4)
                    strike['pe']['vega'] = round(put_greeks['vega'], 4)
                    strike['pe']['theta'] = round(put_greeks['theta'], 4)
                    strike['pe']['rho'] = round(put_greeks['rho'], 4)
            except Exception as e:
                pass

        return strikes

    @staticmethod
    def _calculate_greeks(S: float, K: float, T: float, sigma: float,
                         option_type: str = 'call') -> Dict[str, float]:
        """
        Calculate all Greeks using Black-Scholes

        Args:
            S: Spot price
            K: Strike price
            T: Time to expiration (years)
            sigma: Implied volatility
            option_type: 'call' or 'put'

        Returns:
            Dict with Delta, Gamma, Vega, Theta, Rho
        """
        r = GreeksInjector.RISK_FREE_RATE

        if T <= 0 or sigma <= 0:
            return {
                'delta': 0.5 if option_type == 'call' else -0.5,
                'gamma': 0,
                'vega': 0,
                'theta': 0,
                'rho': 0
            }

        # Calculate d1 and d2
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)

        # Get standard normal distribution values
        N_d1 = norm.cdf(d1)
        N_d2 = norm.cdf(d2)
        n_d1 = norm.pdf(d1)

        if option_type == 'call':
            delta = N_d1
            theta = (-(S * n_d1 * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * N_d2) / 365
            rho = K * T * math.exp(-r * T) * N_d2 / 100
        else:  # put
            delta = N_d1 - 1
            theta = (-(S * n_d1 * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * (1 - N_d2)) / 365
            rho = -K * T * math.exp(-r * T) * (1 - N_d2) / 100

        # Greeks common to both
        gamma = n_d1 / (S * sigma * math.sqrt(T))
        vega = S * n_d1 * math.sqrt(T) / 100

        return {
            'delta': delta,
            'gamma': gamma,
            'vega': vega,
            'theta': theta,
            'rho': rho
        }

    @staticmethod
    def _calculate_iv(S: float, K: float, option_price: float, T: float,
                     is_call: bool = True, initial_guess: float = 0.25) -> float:
        """
        Calculate Implied Volatility using Newton-Raphson method

        Args:
            S: Spot price
            K: Strike price
            option_price: Market price of option
            T: Time to expiration (years)
            is_call: True for call, False for put
            initial_guess: Initial IV guess

        Returns:
            Implied Volatility
        """
        r = GreeksInjector.RISK_FREE_RATE
        sigma = initial_guess

        try:
            for _ in range(100):  # Max iterations
                # Calculate option price with current sigma
                d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
                d2 = d1 - sigma * math.sqrt(T)

                if is_call:
                    calc_price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
                else:
                    calc_price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

                # Vega (derivative of option price w.r.t. volatility)
                vega = S * norm.pdf(d1) * math.sqrt(T)

                if abs(vega) < 1e-7:
                    break

                # Newton-Raphson update
                diff = calc_price - option_price
                sigma = sigma - diff / vega

                if abs(diff) < 1e-6:
                    break

                sigma = max(0.01, min(2.0, sigma))  # Keep sigma between 1% and 200%

            return sigma
        except:
            return GreeksInjector.IMPLIED_VOLATILITY


class OptionGreeksAnalyzer:
    """Analyzes Greeks for trading decisions"""

    @staticmethod
    def get_delta_neutral_hedge(call_delta: float, put_delta: float,
                                contract_size: int = 100) -> Dict:
        """Get delta-neutral hedge ratios"""
        return {
            "call_delta": call_delta,
            "put_delta": put_delta,
            "hedge_ratio": abs(put_delta / call_delta) if call_delta != 0 else 0,
            "strategy": "Long call + Long put" if call_delta > 0 and put_delta < 0 else "Unknown"
        }

    @staticmethod
    def get_vega_exposure(call_vega: float, put_vega: float,
                         contracts: int = 1) -> Dict:
        """Calculate vega exposure (volatility sensitivity)"""
        total_vega = (call_vega + put_vega) * contracts
        return {
            "call_vega": call_vega,
            "put_vega": put_vega,
            "total_vega": round(total_vega, 4),
            "1pct_vol_move": round(total_vega * 0.01, 2),
            "volatility_outlook": "Buy vol" if total_vega > 0 else "Sell vol"
        }

    @staticmethod
    def get_theta_decay(call_theta: float, put_theta: float) -> Dict:
        """Time decay analysis"""
        total_theta = call_theta + put_theta
        return {
            "call_theta": round(call_theta, 4),
            "put_theta": round(put_theta, 4),
            "total_theta": round(total_theta, 4),
            "daily_pnl_from_decay": round(total_theta, 2),
            "strategy": "Time decay beneficiary (short)" if total_theta > 0 else "Time decay victim (long)"
        }


if __name__ == "__main__":
    # Test Greeks calculation
    spot = 24000
    strike = 24000
    call_price = 300
    put_price = 300
    days = 1

    test_strike = {
        'strike': strike,
        'ce': {'ltp': call_price, 'oi': 1000000, 'vol': 10000},
        'pe': {'ltp': put_price, 'oi': 1000000, 'vol': 10000}
    }

    strikes = [test_strike]
    result = GreeksInjector.inject_greeks_into_strikes(strikes, spot, call_price, put_price, days)

    print("✅ Greeks Calculator Test")
    print(f"Call Greeks: {result[0]['ce']}")
    print(f"Put Greeks: {result[0]['pe']}")
