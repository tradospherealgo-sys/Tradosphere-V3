"""
Trading Routes - Paper trading, signals, and live market data
"""

from datetime import datetime
from flask import Blueprint, request, g
from auth_manager_v3_1 import AuthDecorator
from paper_trading_model_v3_1 import (
    PaperAccount, PaperTrade, SignalTracking, SessionLocal as PaperSession,
    get_or_create_account, open_trade, close_trade, get_account_trades,
    track_signal, close_signal
)
from response_handler import APIResponse

trading_bp = Blueprint('trading', __name__, url_prefix='/api/trading')


@trading_bp.route('/account/<symbol>', methods=['GET'])
@AuthDecorator.token_required
def get_paper_account(symbol):
    """Get or create paper trading account for symbol"""
    try:
        user_id = g.user_id
        initial_capital = float(request.args.get('capital', 100000))

        db = PaperSession()
        account = get_or_create_account(db, user_id, symbol.upper(), initial_capital)
        result = account.to_dict()
        db.close()

        return APIResponse.success(result)

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@trading_bp.route('/account/<symbol>/reset', methods=['POST'])
@AuthDecorator.token_required
def reset_paper_account(symbol):
    """Reset paper trading account to initial capital"""
    try:
        user_id = g.user_id
        symbol = symbol.upper()

        db = PaperSession()
        account = db.query(PaperAccount).filter(
            PaperAccount.user_id == user_id,
            PaperAccount.symbol == symbol
        ).first()

        if not account:
            db.close()
            return APIResponse.not_found("Account not found")

        account.current_balance = account.initial_capital
        account.invested_amount = 0
        account.total_pnl = 0
        account.pnl_percentage = 0
        account.total_trades = 0
        account.winning_trades = 0
        account.losing_trades = 0
        account.win_rate = 0
        account.avg_win = 0
        account.avg_loss = 0
        account.profit_factor = 0
        account.max_drawdown = 0

        db.query(PaperTrade).filter(PaperTrade.account_id == account.id).delete()

        db.commit()
        db.refresh(account)
        result = account.to_dict()
        db.close()

        return APIResponse.success(result)

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@trading_bp.route('/trade/open', methods=['POST'])
@AuthDecorator.token_required
def open_paper_trade():
    """Open a new paper trade"""
    try:
        user_id = g.user_id
        data = request.json

        if not data:
            return APIResponse.bad_request("No data provided")

        account_id = int(data.get('account_id'))
        symbol = data.get('symbol', '').upper()
        trade_type = data.get('trade_type', 'BUY')
        signal_type = data.get('signal_type', 'TECHNICAL')
        entry_price = float(data.get('entry_price'))
        quantity = int(data.get('quantity'))
        stop_loss = float(data.get('stop_loss')) if data.get('stop_loss') else None
        take_profit = float(data.get('take_profit')) if data.get('take_profit') else None
        signal_desc = data.get('signal_description', '')

        db = PaperSession()

        account = db.query(PaperAccount).filter(
            PaperAccount.id == account_id,
            PaperAccount.user_id == user_id
        ).first()

        if not account:
            db.close()
            return APIResponse.not_found("Account not found")

        required_balance = entry_price * quantity
        if account.current_balance < required_balance:
            db.close()
            return APIResponse.bad_request(
                f"Insufficient balance. Required: {required_balance}, Available: {account.current_balance}"
            )

        trade = open_trade(
            db, account_id, symbol, trade_type, signal_type,
            entry_price, quantity, stop_loss, take_profit, signal_desc
        )

        result = trade.to_dict()
        db.close()

        return APIResponse.success(result, http_status=201)

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@trading_bp.route('/trade/<int:trade_id>/close', methods=['POST'])
@AuthDecorator.token_required
def close_paper_trade(trade_id):
    """Close a paper trade"""
    try:
        user_id = g.user_id
        data = request.json

        if not data or 'exit_price' not in data:
            return APIResponse.bad_request("Exit price required")

        exit_price = float(data.get('exit_price'))

        db = PaperSession()

        trade = db.query(PaperTrade).filter(PaperTrade.id == trade_id).first()
        if not trade:
            db.close()
            return APIResponse.not_found("Trade not found")

        account = db.query(PaperAccount).filter(
            PaperAccount.id == trade.account_id,
            PaperAccount.user_id == user_id
        ).first()

        if not account:
            db.close()
            return APIResponse.forbidden("Unauthorized to close this trade")

        trade = close_trade(db, trade_id, exit_price)
        result = trade.to_dict()
        db.close()

        return APIResponse.success(result)

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@trading_bp.route('/trades/<int:account_id>', methods=['GET'])
@AuthDecorator.token_required
def get_trades(account_id):
    """Get all trades for a paper account"""
    try:
        user_id = g.user_id
        limit = request.args.get('limit', 50, type=int)

        db = PaperSession()

        account = db.query(PaperAccount).filter(
            PaperAccount.id == account_id,
            PaperAccount.user_id == user_id
        ).first()

        if not account:
            db.close()
            return APIResponse.not_found("Account not found")

        trades = get_account_trades(db, account_id, limit)
        result = [t.to_dict() for t in trades]
        db.close()

        return APIResponse.success({
            "trades": result,
            "count": len(result)
        })

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@trading_bp.route('/signal/track', methods=['POST'])
@AuthDecorator.token_required
def track_new_signal():
    """Track a new signal for accuracy monitoring"""
    try:
        user_id = g.user_id
        data = request.json

        if not data:
            return APIResponse.bad_request("No data provided")

        symbol = data.get('symbol', '').upper()
        signal_type = data.get('signal_type', 'TECHNICAL')
        direction = data.get('direction', 'BUY')
        entry_price = float(data.get('entry_price'))
        target_price = float(data.get('target_price'))
        stop_loss = float(data.get('stop_loss'))
        desc = data.get('description', '')

        db = PaperSession()
        signal = track_signal(db, user_id, symbol, signal_type, direction, entry_price, target_price, stop_loss, desc)

        result = signal.to_dict()
        db.close()

        return APIResponse.success(result, http_status=201)

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@trading_bp.route('/signal/<int:signal_id>/close', methods=['POST'])
@AuthDecorator.token_required
def close_tracked_signal(signal_id):
    """Close a tracked signal and calculate accuracy"""
    try:
        user_id = g.user_id
        data = request.json

        if not data or 'outcome_price' not in data:
            return APIResponse.bad_request("Outcome price required")

        outcome_price = float(data.get('outcome_price'))

        db = PaperSession()

        signal = db.query(SignalTracking).filter(
            SignalTracking.id == signal_id,
            SignalTracking.user_id == user_id
        ).first()

        if not signal:
            db.close()
            return APIResponse.not_found("Signal not found")

        signal = close_signal(db, signal_id, outcome_price)
        result = signal.to_dict()
        db.close()

        return APIResponse.success(result)

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@trading_bp.route('/signals/user', methods=['GET'])
@AuthDecorator.token_required
def get_user_signals():
    """Get all tracked signals for user"""
    try:
        user_id = g.user_id
        limit = request.args.get('limit', 50, type=int)

        db = PaperSession()
        signals = db.query(SignalTracking).filter(
            SignalTracking.user_id == user_id
        ).order_by(SignalTracking.generated_at.desc()).limit(limit).all()

        result = [s.to_dict() for s in signals]
        db.close()

        return APIResponse.success({
            "signals": result,
            "count": len(result)
        })

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@trading_bp.route('/stats/<int:account_id>', methods=['GET'])
@AuthDecorator.token_required
def get_trading_stats(account_id):
    """Get comprehensive trading statistics for account"""
    try:
        user_id = g.user_id

        db = PaperSession()

        account = db.query(PaperAccount).filter(
            PaperAccount.id == account_id,
            PaperAccount.user_id == user_id
        ).first()

        if not account:
            db.close()
            return APIResponse.not_found("Account not found")

        trades = db.query(PaperTrade).filter(
            PaperTrade.account_id == account_id,
            PaperTrade.status == "closed"
        ).all()

        winning_pnl = sum([t.pnl for t in trades if t.pnl > 0])
        losing_pnl = sum([t.pnl for t in trades if t.pnl < 0])

        if account.winning_trades > 0:
            avg_win = winning_pnl / account.winning_trades
        else:
            avg_win = 0

        if account.losing_trades > 0:
            avg_loss = abs(losing_pnl) / account.losing_trades
        else:
            avg_loss = 0

        if avg_loss > 0:
            profit_factor = avg_win / avg_loss if avg_win > 0 else 0
        else:
            profit_factor = 0

        account.avg_win = avg_win
        account.avg_loss = avg_loss
        account.profit_factor = profit_factor

        db.commit()

        result = account.to_dict()
        db.close()

        return APIResponse.success(result)

    except Exception as e:
        return APIResponse.server_error(str(e), e)


@trading_bp.route('/signal-accuracy/user', methods=['GET'])
@AuthDecorator.token_required
def get_signal_accuracy():
    """Get signal accuracy statistics"""
    try:
        user_id = g.user_id

        db = PaperSession()

        all_signals = db.query(SignalTracking).filter(
            SignalTracking.user_id == user_id,
            SignalTracking.is_winning.isnot(None)
        ).all()

        if not all_signals:
            db.close()
            return APIResponse.success({
                "total_signals": 0,
                "winning_signals": 0,
                "losing_signals": 0,
                "win_rate": 0,
                "avg_accuracy": 0
            })

        winning = sum(1 for s in all_signals if s.is_winning)
        losing = len(all_signals) - winning
        accuracy_scores = [s.accuracy_score for s in all_signals if s.accuracy_score]
        avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0

        db.close()

        return APIResponse.success({
            "total_signals": len(all_signals),
            "winning_signals": winning,
            "losing_signals": losing,
            "win_rate": (winning / len(all_signals) * 100) if all_signals else 0,
            "avg_accuracy": avg_accuracy
        })

    except Exception as e:
        return APIResponse.server_error(str(e), e)
