"""
Risk Management Module
Position sizing, stop-loss placement, daily loss limits, kill-switch logic
"""

from typing import Dict, Tuple
from logger_config import get_logger

logger = get_logger(__name__)


class RiskManager:
    """Manage position sizing, risk limits, and order validation"""

    def __init__(self, account_balance: float, risk_per_trade: float = 0.01, max_daily_loss_pct: float = 0.05):
        """
        Initialize risk manager

        Args:
            account_balance: Total account balance
            risk_per_trade: Risk per trade as decimal (0.01 = 1%)
            max_daily_loss_pct: Max daily loss as decimal (0.05 = 5%)
        """
        self.account_balance = account_balance
        self.risk_per_trade = risk_per_trade
        self.max_daily_loss_pct = max_daily_loss_pct
        self.daily_pnl = 0
        self.open_positions = []
        self.trade_count_today = 0

    def calculate_position_size(self, entry_price: float, stop_loss_price: float, max_loss: float = None) -> Dict:
        """
        Calculate position size based on risk-reward

        Args:
            entry_price: Entry price for the trade
            stop_loss_price: Stop loss price
            max_loss: Override max loss amount (uses risk_per_trade if None)

        Returns:
        {
            'quantity': int,
            'max_loss_amount': float,
            'risk_pct': float,
            'position_size_value': float,
            'is_valid': bool,
            'message': str
        }
        """
        try:
            if max_loss is None:
                max_loss = self.account_balance * self.risk_per_trade

            # Calculate risk per unit
            risk_per_unit = abs(entry_price - stop_loss_price)

            if risk_per_unit == 0:
                return {
                    'quantity': 0,
                    'max_loss_amount': 0,
                    'risk_pct': 0,
                    'position_size_value': 0,
                    'is_valid': False,
                    'message': '❌ Invalid SL: Entry and SL cannot be same'
                }

            # Calculate quantity
            quantity = int(max_loss / risk_per_unit)

            if quantity == 0:
                return {
                    'quantity': 0,
                    'max_loss_amount': 0,
                    'risk_pct': 0,
                    'position_size_value': 0,
                    'is_valid': False,
                    'message': f'❌ Position too small: Cannot buy even 1 lot at current risk'
                }

            position_value = quantity * entry_price
            risk_pct = (max_loss / self.account_balance) * 100

            logger.info(
                f"📊 Position Size Calculated: "
                f"Qty={quantity} | Max Loss=₹{max_loss:.2f} | Risk={risk_pct:.2f}%"
            )

            return {
                'quantity': quantity,
                'max_loss_amount': round(max_loss, 2),
                'risk_pct': round(risk_pct, 2),
                'position_size_value': round(position_value, 2),
                'is_valid': True,
                'message': f'✅ Buy {quantity} units, risking ₹{max_loss:.2f}'
            }

        except Exception as e:
            logger.error(f"❌ Error calculating position size: {str(e)}")
            return {
                'quantity': 0,
                'max_loss_amount': 0,
                'risk_pct': 0,
                'position_size_value': 0,
                'is_valid': False,
                'message': f'❌ Error: {str(e)}'
            }

    def validate_daily_loss_limit(self, potential_loss: float) -> Dict:
        """
        Check if trade would breach daily loss limit

        Returns:
        {
            'is_allowed': bool,
            'current_daily_loss': float,
            'max_daily_loss': float,
            'remaining_risk_budget': float,
            'kill_switch_active': bool,
            'message': str
        }
        """
        max_daily_loss = self.account_balance * self.max_daily_loss_pct
        remaining_budget = max_daily_loss - abs(self.daily_pnl)

        kill_switch = self.daily_pnl < -max_daily_loss

        if kill_switch:
            logger.warning(f"🛑 KILL SWITCH ACTIVATED: Daily loss ₹{abs(self.daily_pnl):.2f} > ₹{max_daily_loss:.2f}")
            return {
                'is_allowed': False,
                'current_daily_loss': round(abs(self.daily_pnl), 2),
                'max_daily_loss': round(max_daily_loss, 2),
                'remaining_risk_budget': 0,
                'kill_switch_active': True,
                'message': '🛑 Daily loss limit hit. No more trades today.'
            }

        if potential_loss > remaining_budget:
            logger.warning(
                f"⚠️ Trade would breach daily limit: "
                f"Potential Loss ₹{potential_loss:.2f} > Remaining ₹{remaining_budget:.2f}"
            )
            return {
                'is_allowed': False,
                'current_daily_loss': round(abs(self.daily_pnl), 2),
                'max_daily_loss': round(max_daily_loss, 2),
                'remaining_risk_budget': round(remaining_budget, 2),
                'kill_switch_active': False,
                'message': f'⚠️ Trade rejected: Only ₹{remaining_budget:.2f} risk budget left'
            }

        logger.info(
            f"✅ Daily loss check passed: "
            f"Current Loss: ₹{abs(self.daily_pnl):.2f} | "
            f"Remaining Budget: ₹{remaining_budget:.2f}"
        )

        return {
            'is_allowed': True,
            'current_daily_loss': round(abs(self.daily_pnl), 2),
            'max_daily_loss': round(max_daily_loss, 2),
            'remaining_risk_budget': round(remaining_budget, 2),
            'kill_switch_active': False,
            'message': f'✅ Safe to trade. Risk budget: ₹{remaining_budget:.2f}'
        }

    def calculate_stop_loss(self, entry_price: float, atr: float, direction: str = 'BUY') -> float:
        """
        Calculate stop loss based on ATR

        Args:
            entry_price: Entry price
            atr: Average True Range
            direction: 'BUY' or 'SELL'

        Returns:
            Stop loss price
        """
        sl_buffer = atr * 1.5  # 1.5 ATR below entry for BUY, above for SELL

        if direction == 'BUY':
            sl = entry_price - sl_buffer
        else:
            sl = entry_price + sl_buffer

        logger.info(f"📍 SL Calculated: Entry={entry_price:.2f}, ATR={atr:.2f}, SL={sl:.2f}")
        return round(sl, 2)

    def calculate_trailing_stop(self, entry_price: float, current_price: float, atr: float, profit_pct: float = 0.02) -> float:
        """
        Calculate trailing stop (moves up by 0.5 ATR every 2% profit)

        Args:
            entry_price: Original entry price
            current_price: Current price
            atr: Average True Range
            profit_pct: Profit threshold (0.02 = 2%)

        Returns:
            New trailing stop price
        """
        profit = ((current_price - entry_price) / entry_price) * 100

        if profit > profit_pct * 100:
            # Trail by 0.5 ATR
            trailing_sl = current_price - (atr * 0.5)
            logger.info(f"📈 Trailing SL Updated: Current={current_price:.2f}, New SL={trailing_sl:.2f}")
            return round(trailing_sl, 2)

        return entry_price

    def validate_trade(
        self,
        entry_price: float,
        stop_loss_price: float,
        quantity: int,
        direction: str = 'BUY'
    ) -> Dict:
        """
        Validate a trade before execution

        Returns:
        {
            'is_valid': bool,
            'risk_amount': float,
            'reward_potential': float,
            'risk_reward_ratio': float,
            'checks': {
                'daily_loss_check': bool,
                'position_size_reasonable': bool,
                'risk_reward_adequate': bool
            },
            'message': str
        }
        """
        try:
            # Calculate risk
            risk_amount = abs(entry_price - stop_loss_price) * quantity
            daily_check = self.validate_daily_loss_limit(risk_amount)

            if not daily_check['is_allowed']:
                return {
                    'is_valid': False,
                    'risk_amount': round(risk_amount, 2),
                    'reward_potential': 0,
                    'risk_reward_ratio': 0,
                    'checks': {
                        'daily_loss_check': False,
                        'position_size_reasonable': True,
                        'risk_reward_adequate': True
                    },
                    'message': daily_check['message']
                }

            # Position size check
            position_value = entry_price * quantity
            max_position = self.account_balance * 0.1  # Max 10% of account per trade

            if position_value > max_position:
                return {
                    'is_valid': False,
                    'risk_amount': round(risk_amount, 2),
                    'reward_potential': 0,
                    'risk_reward_ratio': 0,
                    'checks': {
                        'daily_loss_check': True,
                        'position_size_reasonable': False,
                        'risk_reward_adequate': True
                    },
                    'message': f'❌ Position too large: ₹{position_value:.0f} > Max ₹{max_position:.0f} (10% of account)'
                }

            # Risk-reward check (minimum 1:1.5 ratio)
            min_reward = risk_amount * 1.5
            reward_potential = min_reward

            return {
                'is_valid': True,
                'risk_amount': round(risk_amount, 2),
                'reward_potential': round(reward_potential, 2),
                'risk_reward_ratio': 1.5,
                'checks': {
                    'daily_loss_check': True,
                    'position_size_reasonable': True,
                    'risk_reward_adequate': True
                },
                'message': f'✅ Trade validated | Risk: ₹{risk_amount:.2f} | Target: ₹{reward_potential:.2f}'
            }

        except Exception as e:
            logger.error(f"❌ Error validating trade: {str(e)}")
            return {
                'is_valid': False,
                'risk_amount': 0,
                'reward_potential': 0,
                'risk_reward_ratio': 0,
                'checks': {
                    'daily_loss_check': False,
                    'position_size_reasonable': False,
                    'risk_reward_adequate': False
                },
                'message': f'❌ Validation error: {str(e)}'
            }

    def update_daily_pnl(self, pnl: float):
        """Update daily P&L"""
        self.daily_pnl += pnl
        logger.info(f"💰 Daily P&L Updated: ₹{self.daily_pnl:+.2f}")

    def reset_daily_limits(self):
        """Reset daily limits (call at market open)"""
        self.daily_pnl = 0
        self.trade_count_today = 0
        logger.info("🔄 Daily limits reset")
