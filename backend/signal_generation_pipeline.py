"""
Signal Generation Pipeline
Complete end-to-end pipeline: Market Data -> Options Chain -> Signal Generation
"""

from typing import Dict, Optional
from datetime import datetime
from logger_config import get_logger
from market_regime import MarketRegime
from angel_one_options_handler import AngelOneOptionsHandler
from composite_signal_generator import CompositeSignalGenerator
from risk_manager import RiskManager

logger = get_logger(__name__)


class SignalGenerationPipeline:
    """Complete pipeline for generating professional trading signals"""

    def __init__(self, symbol: str, account_balance: float = 100000, risk_per_trade: float = 0.01):
        """
        Initialize signal generation pipeline

        Args:
            symbol: Trading symbol (e.g., 'NIFTY50')
            account_balance: Total account balance
            risk_per_trade: Risk per trade (0.01 = 1%)
        """
        self.symbol = symbol
        self.account_balance = account_balance

        # Initialize modules
        self.market_regime = MarketRegime()
        self.signal_generator = CompositeSignalGenerator()
        self.risk_manager = RiskManager(account_balance, risk_per_trade)
        self.options_handler = None

        logger.info(f"✅ Signal Generation Pipeline initialized for {symbol}")

    def generate_signal_complete(
        self,
        spot_price: float,
        candles: list,
        ema_fast: float,
        ema_slow: float,
        ema_long: float,
        rsi: float,
        bb_position: float,
        macd_signal: str,
        volume_confirm: bool,
        options_chain_response: Dict,
        expiry_date: str = "25JUN2026",
        expiry_days: int = 7
    ) -> Dict:
        """
        Generate complete professional signal with all components

        Args:
            spot_price: Current spot price
            candles: List of OHLC candles
            ema_fast: Fast EMA (20)
            ema_slow: Medium EMA (50)
            ema_long: Long EMA (200)
            rsi: RSI value
            bb_position: Bollinger Band position (-1 to 1)
            macd_signal: MACD direction ('BULLISH' or 'BEARISH')
            volume_confirm: Volume confirmation boolean
            options_chain_response: Options chain data from Angel One
            expiry_date: Option expiry date
            expiry_days: Days to expiration

        Returns: Complete professional signal with all analysis
        """
        try:
            logger.info(f"📊 Generating complete signal for {self.symbol} | Spot: {spot_price}")

            # STEP 1: Market Regime Detection
            regime_data = self.market_regime.detect_regime(
                candles, ema_fast, ema_slow, spot_price
            )
            logger.info(f"📈 Regime: {regime_data['regime']} (Strength: {regime_data['regime_strength']}%)")

            # STEP 2: Technical Scoring
            tech_score = self.signal_generator.score_technical_indicators(
                ema_fast, ema_slow, ema_long, rsi, bb_position, macd_signal, volume_confirm
            )
            logger.info(f"🔧 Technical Score: {tech_score['score']}/40")

            # STEP 3: Regime Scoring
            regime_score = self.signal_generator.score_market_regime(regime_data)
            logger.info(f"📊 Regime Score: {regime_score['score']}/30")

            # STEP 4: Options Analysis
            self.options_handler = AngelOneOptionsHandler(None, self.symbol, expiry_date)
            options_analysis = self.options_handler.parse_chain_and_analyze(
                options_chain_response, expiry_days
            )

            options_score = self._score_options_context(options_analysis)
            logger.info(f"📉 Options Score: {options_score['score']}/20")

            # STEP 5: Risk Validation
            risk_score = self._score_risk_validation(spot_price, ema_slow)
            logger.info(f"⚠️ Risk Score: {risk_score['score']}/10")

            # STEP 6: Price Level Detection
            current_price_level = self._detect_price_level(spot_price, candles, ema_slow)
            at_resistance = current_price_level == 'RESISTANCE'
            at_support = current_price_level == 'SUPPORT'

            # STEP 7: OI Buildup Direction
            oi_buildup_direction = options_analysis.get('oi_analysis', {}).get('oi_buildup', {}).get('direction')

            # STEP 8: Generate Composite Signal
            signal = self.signal_generator.generate_signal(
                technical_score=tech_score,
                regime_score=regime_score,
                options_score=options_score,
                risk_score=risk_score,
                current_price=spot_price,
                entry_price=spot_price,
                current_price_level=current_price_level,
                oi_buildup_direction=oi_buildup_direction,
                at_resistance=at_resistance,
                at_support=at_support
            )

            # STEP 9: Add Extended Analysis
            extended_analysis = {
                'timestamp': datetime.now().isoformat(),
                'symbol': self.symbol,
                'spot_price': spot_price,
                'regime': regime_data,
                'options_analysis': options_analysis.get('chain_summary', {}),
                'expected_move': options_analysis.get('expected_move', {}),
                'oi_context': options_analysis.get('oi_analysis', {}),
                'skew_analysis': options_analysis.get('skew', {}),
                'atm_options': options_analysis.get('atm_options', {}),
            }

            # Combine signal with extended data
            complete_signal = {
                **signal,
                'extended_analysis': extended_analysis
            }

            logger.info(
                f"✅ SIGNAL GENERATED: {signal['signal']} | "
                f"Confidence: {signal['confidence_score']}% | "
                f"Risk: {signal['risk_level']}"
            )

            return complete_signal

        except Exception as e:
            logger.error(f"❌ Error generating complete signal: {str(e)}")
            return {
                'error': str(e),
                'signal': 'ERROR',
                'confidence_score': 0,
                'action': 'AVOID'
            }

    def _score_options_context(self, options_analysis: Dict) -> Dict:
        """Score options context for signal generation"""
        try:
            score = 0
            details = []

            oi_data = options_analysis.get('oi_analysis', {})
            pcr = oi_data.get('pcr', {})
            max_pain = oi_data.get('max_pain', {})
            oi_buildup = oi_data.get('oi_buildup', {})

            # PCR scoring (0-8 points)
            if pcr.get('signal') == 'BULLISH':
                score += 8
                details.append("Bullish PCR")
            elif pcr.get('signal') == 'BEARISH':
                score -= 8
                details.append("Bearish PCR")
            else:
                score += 3
                details.append("Neutral PCR")

            # Max Pain scoring (0-7 points)
            if max_pain.get('bias') == 'UPSIDE':
                score += 7
                details.append("Upside bias from Max Pain")
            elif max_pain.get('bias') == 'DOWNSIDE':
                score -= 7
                details.append("Downside bias from Max Pain")

            # OI Buildup scoring (0-5 points)
            if oi_buildup.get('direction') == 'CALL_OI_BUILDUP':
                score += 5
                details.append("Call OI accumulation")
            elif oi_buildup.get('direction') == 'PUT_OI_BUILDUP':
                score -= 5
                details.append("Put OI accumulation")

            return {
                'score': max(0, score),
                'pcr_signal': pcr.get('signal', 'NEUTRAL'),
                'max_pain_bias': max_pain.get('bias', 'NEUTRAL'),
                'details': ' | '.join(details)
            }

        except Exception as e:
            logger.error(f"❌ Error scoring options: {str(e)}")
            return {'score': 0, 'details': 'Error in options scoring'}

    def _score_risk_validation(self, entry_price: float, stop_loss_price: float) -> Dict:
        """Score risk validation"""
        try:
            # Validate trade risk
            validation = self.risk_manager.validate_trade(
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                quantity=1,
                direction='BUY'
            )

            if validation.get('is_valid'):
                return {
                    'score': 10,
                    'details': validation.get('message', 'Risk approved')
                }
            else:
                return {
                    'score': 0,
                    'details': validation.get('message', 'Risk rejected')
                }

        except Exception as e:
            logger.error(f"❌ Error validating risk: {str(e)}")
            return {'score': 0, 'details': f'Risk validation error: {str(e)}'}

    def _detect_price_level(self, spot_price: float, candles: list, support_level: float) -> str:
        """Detect if price is at support, resistance, breakout, or neutral"""
        try:
            if not candles or len(candles) < 5:
                return 'NEUTRAL'

            # Get recent high and low
            recent_high = max([c['high'] for c in candles[-5:]])
            recent_low = min([c['low'] for c in candles[-5:]])
            range_pct = ((recent_high - recent_low) / recent_low) * 100

            # Detect level
            high_distance = ((recent_high - spot_price) / recent_high) * 100
            low_distance = ((spot_price - recent_low) / recent_low) * 100

            if high_distance < 0.5:
                return 'RESISTANCE'
            elif low_distance < 0.5:
                return 'SUPPORT'
            elif spot_price > recent_high:
                return 'BREAKOUT'
            else:
                return 'NEUTRAL'

        except Exception as e:
            logger.error(f"⚠️ Error detecting price level: {str(e)}")
            return 'NEUTRAL'
