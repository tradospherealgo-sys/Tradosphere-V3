"""
Backtesting Routes - API endpoints for strategy backtesting
"""

from flask import Blueprint, jsonify, request, g
from auth_manager import AuthDecorator
from backtesting_engine import Backtest, TechnicalStrategy, MomentumStrategy
from datetime import datetime

backtest_bp = Blueprint('backtest', __name__, url_prefix='/api/backtest')


@backtest_bp.route('/strategies', methods=['GET'])
@AuthDecorator.token_required
def get_available_strategies():
    """Get list of available backtesting strategies"""
    try:
        return jsonify({
            "status": "success",
            "strategies": [
                {
                    "id": "technical",
                    "name": "Technical-Based Strategy",
                    "description": "Uses RSI < 30 for buy and EMA crossover signals",
                    "indicators": ["RSI", "EMA 9", "EMA 50"]
                },
                {
                    "id": "momentum",
                    "name": "Momentum-Based Strategy",
                    "description": "Uses RSI oversold (< 30) for buy and overbought (> 70) for sell",
                    "indicators": ["RSI"]
                }
            ]
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@backtest_bp.route('/run', methods=['POST'])
@AuthDecorator.token_required
def run_backtest():
    """Run a single strategy backtest"""
    try:
        user_id = g.user_id
        data = request.json

        symbol = data.get('symbol', 'NIFTY').upper()
        strategy_id = data.get('strategy', 'technical')
        interval = data.get('interval', '15')
        days_back = int(data.get('days_back', 30))
        initial_capital = float(data.get('initial_capital', 100000))

        # Select strategy
        if strategy_id == 'technical':
            strategy = TechnicalStrategy()
        elif strategy_id == 'momentum':
            strategy = MomentumStrategy()
        else:
            return jsonify({
                "status": "error",
                "message": f"Unknown strategy: {strategy_id}"
            }), 400

        # Run backtest
        result = Backtest.run(
            symbol=symbol,
            strategy=strategy,
            interval=interval,
            days_back=days_back,
            initial_capital=initial_capital
        )

        if result.get("status") == "success":
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@backtest_bp.route('/compare', methods=['POST'])
@AuthDecorator.token_required
def compare_strategies():
    """Compare all available strategies on same data"""
    try:
        user_id = g.user_id
        data = request.json

        symbol = data.get('symbol', 'NIFTY').upper()
        interval = data.get('interval', '15')
        days_back = int(data.get('days_back', 30))
        initial_capital = float(data.get('initial_capital', 100000))

        # Run comparison
        result = Backtest.compare_strategies(
            symbol=symbol,
            interval=interval,
            days_back=days_back,
            initial_capital=initial_capital
        )

        return jsonify({
            "status": "success",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@backtest_bp.route('/optimize', methods=['POST'])
@AuthDecorator.token_required
def optimize_strategy():
    """Optimize strategy parameters (placeholder)"""
    try:
        return jsonify({
            "status": "success",
            "message": "Strategy optimization coming soon",
            "data": {
                "best_parameters": {
                    "rsi_period": 14,
                    "ema_fast": 9,
                    "ema_slow": 50
                },
                "performance": {
                    "win_rate": 65,
                    "profit_factor": 2.15
                }
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
