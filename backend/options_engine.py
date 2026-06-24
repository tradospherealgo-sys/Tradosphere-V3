"""
Options Engine - Analyze options market data and detect biases
Processes option chain data and generates options market analysis
"""

from typing import Dict, Optional, List

class OptionsEngine:
    """
    Options analysis engine for market data
    Analyzes PCR, OI, volume, IV and detects market bias
    """

    @staticmethod
    def analyze_pcr(put_oi: int, call_oi: int) -> Dict:
        """
        Analyze Put-Call Ratio

        Args:
            put_oi: Put open interest
            call_oi: Call open interest

        Returns:
            Dict with PCR analysis and bias
        """
        if call_oi == 0:
            pcr = 0.0
            bias = "BULLISH"
        else:
            pcr = put_oi / call_oi

        # Interpret PCR
        if pcr > 1.2:
            pcr_bias = "STRONG BULLISH"
            strength = "very_strong"
        elif pcr > 1.0:
            pcr_bias = "BULLISH"
            strength = "strong"
        elif pcr > 0.9:
            pcr_bias = "NEUTRAL"
            strength = "neutral"
        elif pcr > 0.7:
            pcr_bias = "BEARISH"
            strength = "strong"
        else:
            pcr_bias = "STRONG BEARISH"
            strength = "very_strong"

        return {
            "pcr": round(pcr, 3),
            "bias": pcr_bias,
            "strength": strength,
            "put_oi": put_oi,
            "call_oi": call_oi
        }

    @staticmethod
    def analyze_oi_buildup(current_oi: int, previous_oi: int) -> Dict:
        """
        Analyze Open Interest buildup

        Args:
            current_oi: Current OI
            previous_oi: Previous OI

        Returns:
            Dict with OI change analysis
        """
        if previous_oi == 0:
            oi_change_pct = 0.0
        else:
            oi_change_pct = ((current_oi - previous_oi) / previous_oi) * 100

        # Interpret OI change
        if oi_change_pct > 5:
            oi_trend = "STRONG BUILDUP"
            interpretation = "Positions being added"
        elif oi_change_pct > 1:
            oi_trend = "BUILDUP"
            interpretation = "Slight position increase"
        elif oi_change_pct < -5:
            oi_trend = "STRONG UNWINDING"
            interpretation = "Positions being closed"
        elif oi_change_pct < -1:
            oi_trend = "UNWINDING"
            interpretation = "Slight position decrease"
        else:
            oi_trend = "STABLE"
            interpretation = "OI relatively stable"

        return {
            "change_percent": round(oi_change_pct, 2),
            "trend": oi_trend,
            "interpretation": interpretation,
            "current_oi": current_oi,
            "previous_oi": previous_oi
        }

    @staticmethod
    def analyze_option_chain(call_oi: int, put_oi: int, call_volume: int,
                            put_volume: int) -> Dict:
        """
        Analyze options market activity

        Args:
            call_oi: Call open interest
            put_oi: Put open interest
            call_volume: Call volume
            put_volume: Put volume

        Returns:
            Dict with options analysis
        """
        # Analyze volume
        if call_volume + put_volume == 0:
            call_volume_pct = 0
            put_volume_pct = 0
        else:
            total_volume = call_volume + put_volume
            call_volume_pct = (call_volume / total_volume) * 100
            put_volume_pct = (put_volume / total_volume) * 100

        # Volume bias
        if call_volume_pct > 55:
            volume_bias = "CALL DOMINATED"
        elif put_volume_pct > 55:
            volume_bias = "PUT DOMINATED"
        else:
            volume_bias = "BALANCED"

        return {
            "call_volume_pct": round(call_volume_pct, 2),
            "put_volume_pct": round(put_volume_pct, 2),
            "volume_bias": volume_bias,
            "total_volume": call_volume + put_volume
        }

    @staticmethod
    def calculate_support_resistance(option_strikes: List[Dict],
                                    spot_price: float) -> Dict:
        """
        Calculate support and resistance from option chain

        Args:
            option_strikes: List of option strike dicts with high, low OI
            spot_price: Current spot price

        Returns:
            Dict with support and resistance levels
        """
        # Find max OI levels
        max_call_oi = 0
        max_put_oi = 0
        max_call_strike = spot_price
        max_put_strike = spot_price

        for strike in option_strikes:
            option_type = strike.get("type", "")
            strike_price = strike.get("strike", 0)
            oi = strike.get("oi", 0)

            if option_type == "CALL" and oi > max_call_oi:
                max_call_oi = oi
                max_call_strike = strike_price

            if option_type == "PUT" and oi > max_put_oi:
                max_put_oi = oi
                max_put_strike = strike_price

        # Interpret levels
        support = max_put_strike if max_put_oi > 0 else spot_price - 100
        resistance = max_call_strike if max_call_oi > 0 else spot_price + 100

        return {
            "support": round(support, 2),
            "resistance": round(resistance, 2),
            "spot_price": round(spot_price, 2),
            "max_put_oi": max_put_oi,
            "max_call_oi": max_call_oi,
            "max_put_strike": max_put_strike,
            "max_call_strike": max_call_strike
        }

    @staticmethod
    def get_market_bias(pcr: float, volume_bias: str, oi_trend: str) -> str:
        """
        Determine overall market bias from multiple factors

        Args:
            pcr: Put-Call Ratio
            volume_bias: Volume bias string
            oi_trend: OI trend string

        Returns:
            Market bias: "BULLISH", "BEARISH", or "NEUTRAL"
        """
        bias_score = 0

        # PCR contribution
        if pcr > 1.1:
            bias_score += 2  # Bullish
        elif pcr < 0.8:
            bias_score -= 2  # Bearish
        else:
            bias_score += 0  # Neutral

        # Volume contribution
        if "CALL" in volume_bias:
            bias_score -= 1  # Calls dominated = potential selling
        elif "PUT" in volume_bias:
            bias_score += 1  # Puts dominated = potential support

        # OI trend contribution
        if "BUILDUP" in oi_trend:
            if "PUT" in oi_trend or bias_score > 0:
                bias_score += 1
            else:
                bias_score -= 1

        # Final bias determination
        if bias_score >= 2:
            return "BULLISH"
        elif bias_score <= -2:
            return "BEARISH"
        else:
            return "NEUTRAL"

    @staticmethod
    def find_support_resistance(option_chain_data: Dict) -> Dict:
        """
        Find support and resistance levels from option chain

        Args:
            option_chain_data: Option chain data with strikes

        Returns:
            Dict with support and resistance levels
        """
        spot_price = option_chain_data.get("spot_price", 0)
        strikes = option_chain_data.get("strikes", [])

        if not strikes:
            return {
                "support": round(spot_price - 100, 2),
                "resistance": round(spot_price + 100, 2),
                "support_strike": 0,
                "resistance_strike": 0
            }

        # Find max OI levels for support and resistance
        max_pe_oi = 0
        max_ce_oi = 0
        pe_max_strike = spot_price
        ce_max_strike = spot_price

        for strike_data in strikes:
            strike = strike_data.get("strike", 0)
            pe_oi = strike_data.get("pe", {}).get("oi", 0)
            ce_oi = strike_data.get("ce", {}).get("oi", 0)

            if pe_oi > max_pe_oi:
                max_pe_oi = pe_oi
                pe_max_strike = strike

            if ce_oi > max_ce_oi:
                max_ce_oi = ce_oi
                ce_max_strike = strike

        # Support is typically where Put OI is highest (below spot)
        # Resistance is typically where Call OI is highest (above spot)
        support = pe_max_strike if pe_max_strike < spot_price else spot_price - 200
        resistance = ce_max_strike if ce_max_strike > spot_price else spot_price + 200

        return {
            "support": round(support, 2),
            "resistance": round(resistance, 2),
            "support_strike": pe_max_strike,
            "resistance_strike": ce_max_strike,
            "max_pe_oi": max_pe_oi,
            "max_ce_oi": max_ce_oi
        }

    @staticmethod
    def detect_oi_change(current_data: Dict, previous_data: Dict = None) -> Dict:
        """
        Detect changes in open interest (buildup/unwinding)

        Args:
            current_data: Current option chain data
            previous_data: Previous option chain data (optional)

        Returns:
            Dict with OI change analysis
        """
        current_total_oi = (
            current_data.get("total_call_oi", 0) +
            current_data.get("total_put_oi", 0)
        )

        if previous_data:
            previous_total_oi = (
                previous_data.get("total_call_oi", 0) +
                previous_data.get("total_put_oi", 0)
            )
        else:
            previous_total_oi = current_total_oi

        return OptionsEngine.analyze_oi_buildup(current_total_oi, previous_total_oi)

    @staticmethod
    def analyze_options_bias(option_chain_data: Dict) -> Dict:
        """
        Analyze overall options market bias

        Args:
            option_chain_data: Option chain data with all components

        Returns:
            Dict with bias analysis and reasons
        """
        spot_price = option_chain_data.get("spot_price", 0)
        total_ce_oi = option_chain_data.get("total_call_oi", 0)
        total_pe_oi = option_chain_data.get("total_put_oi", 0)
        pcr = option_chain_data.get("pcr", 1.0)
        strikes = option_chain_data.get("strikes", [])

        # PCR bias
        if pcr > 1.2:
            pcr_bias = "STRONG BULLISH"
        elif pcr > 1.0:
            pcr_bias = "BULLISH"
        elif pcr > 0.8:
            pcr_bias = "NEUTRAL"
        else:
            pcr_bias = "BEARISH"

        # Find Max Pain level (most likely profit/loss point for option writers)
        max_pain = OptionsEngine._calculate_max_pain(strikes, spot_price)

        # OI skew analysis (which side has more OI)
        if total_ce_oi > total_pe_oi:
            oi_skew = "CALL HEAVY"
            skew_bias = "BEARISH"
        elif total_pe_oi > total_ce_oi:
            oi_skew = "PUT HEAVY"
            skew_bias = "BULLISH"
        else:
            oi_skew = "BALANCED"
            skew_bias = "NEUTRAL"

        # Support and resistance
        support_resistance = OptionsEngine.find_support_resistance(option_chain_data)

        return {
            "pcr": round(pcr, 3),
            "pcr_bias": pcr_bias,
            "oi_skew": oi_skew,
            "skew_bias": skew_bias,
            "max_pain": max_pain,
            "support": support_resistance["support"],
            "resistance": support_resistance["resistance"],
            "overall_bias": skew_bias if oi_skew != "BALANCED" else pcr_bias
        }

    @staticmethod
    def _calculate_max_pain(strikes: List[Dict], spot_price: float) -> float:
        """Calculate Max Pain level from option chain"""
        if not strikes:
            return spot_price

        # Simplified Max Pain calculation
        # Sum of (strike * (CE_OI + PE_OI)) / total OI
        total_oi_weighted = 0
        total_oi = 0

        for strike_data in strikes:
            strike = strike_data.get("strike", spot_price)
            ce_oi = strike_data.get("ce", {}).get("oi", 0)
            pe_oi = strike_data.get("pe", {}).get("oi", 0)
            total_oi_weighted += strike * (ce_oi + pe_oi)
            total_oi += (ce_oi + pe_oi)

        if total_oi == 0:
            return spot_price

        max_pain = total_oi_weighted / total_oi
        return round(max_pain, 2)

    @staticmethod
    def analyze(option_chain_data: Dict) -> Dict:
        """
        Comprehensive options analysis with full market data

        Args:
            option_chain_data: Dict with option chain data including strikes

        Returns:
            Dict with complete options analysis
        """
        symbol = option_chain_data.get("symbol", "UNKNOWN")
        spot_price = option_chain_data.get("spot_price", 0)
        total_call_oi = option_chain_data.get("total_call_oi", 0)
        total_put_oi = option_chain_data.get("total_put_oi", 0)
        pcr = option_chain_data.get("pcr", 1.0)

        # Calculate derived values for backward compatibility
        call_volume = total_call_oi // 100 if total_call_oi > 0 else 0
        put_volume = total_put_oi // 100 if total_put_oi > 0 else 0

        # Run analyses
        pcr_analysis = OptionsEngine.analyze_pcr(total_put_oi, total_call_oi)
        oi_analysis = OptionsEngine.analyze_oi_buildup(
            total_put_oi + total_call_oi,
            option_chain_data.get("previous_total_oi", total_put_oi + total_call_oi)
        )
        volume_analysis = OptionsEngine.analyze_option_chain(
            total_call_oi, total_put_oi, call_volume, put_volume
        )
        bias_analysis = OptionsEngine.analyze_options_bias(option_chain_data)

        # Determine overall bias
        overall_bias = OptionsEngine.get_market_bias(
            pcr_analysis["pcr"],
            volume_analysis["volume_bias"],
            oi_analysis["trend"]
        )

        return {
            "status": "success",
            "symbol": symbol,
            "bias": overall_bias,
            "pcr": pcr_analysis["pcr"],
            "support": bias_analysis["support"],
            "resistance": bias_analysis["resistance"],
            "max_pain": bias_analysis["max_pain"],
            "oi_skew": bias_analysis["oi_skew"],
            "pcr_analysis": pcr_analysis,
            "oi_analysis": oi_analysis,
            "volume_analysis": volume_analysis,
            "spot_price": round(spot_price, 2),
            "summary": {
                "market_bias": overall_bias,
                "reason": f"PCR {pcr_analysis['bias']} + {volume_analysis['volume_bias']} + {oi_analysis['trend']}"
            }
        }
