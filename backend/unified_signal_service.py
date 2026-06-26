"""
Unified Signal Service - Single Source of Truth for Tradosphere
Wraps System B (SignalGenerator) for consistent signal generation across dashboard and terminal
"""
import logging
logger = logging.getLogger(__name__)


from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
from signal_writer import SignalGenerator
from market_data import AngelOneMarketData
from technical_engine import TechnicalEngine
from options_engine import OptionsEngine
from database import save_signal, Signal


class UnifiedSignalService:
    """
    Single source of truth for all signal generation in Tradosphere.
    Uses System B (SignalGenerator) as the core engine.
    Ensures identical output for dashboard, terminal, and API clients.
    """

    def __init__(self, market_data: Optional[AngelOneMarketData] = None):
        """Initialize with optional market data instance"""
        self.market = market_data
        self.signal_generator = SignalGenerator(market_data)
        self.last_generated_signals = {}

    def generate_signal(self, symbol: str = 'NIFTY') -> Dict:
        """
        Generate a single signal for given symbol.

        Args:
            symbol: NIFTY, BANKNIFTY, or FINNIFTY

        Returns:
            Dict with signal details matching System B format
        """
        try:
            # Validate symbol
            if symbol not in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
                return {
                    'status': 'error',
                    'message': f'Invalid symbol: {symbol}. Use NIFTY, BANKNIFTY, or FINNIFTY'
                }

            # Generate signal using System B
            signal = self.signal_generator._analyze_symbol(symbol, 0)  # price will be fetched internally

            if not signal:
                return {
                    'status': 'no_signal',
                    'symbol': symbol,
                    'message': 'Insufficient data or no setup found',
                    'timestamp': datetime.utcnow().isoformat()
                }

            # Store in local cache
            self.last_generated_signals[symbol] = signal

            # Save to database
            self._save_signal_to_db(symbol, signal)

            # Return signal with consistency markers
            return {
                'status': 'success',
                'signal': signal,
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'System B (SignalGenerator)',
                'consistency_marker': self._generate_consistency_marker(symbol, signal)
            }

        except Exception as e:
            return {
                'status': 'error',
                'symbol': symbol,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    def generate_signals_batch(self, symbols: List[str] = None) -> Dict:
        """
        Generate signals for multiple symbols.

        Args:
            symbols: List of symbols (defaults to [NIFTY, BANKNIFTY, FINNIFTY])

        Returns:
            Dict with signals for all symbols
        """
        if symbols is None:
            symbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY']

        results = {
            'status': 'success',
            'generated_at': datetime.utcnow().isoformat(),
            'signals': {},
            'summary': {
                'total_symbols': len(symbols),
                'successful': 0,
                'failed': 0,
                'no_signal': 0
            }
        }

        for symbol in symbols:
            result = self.generate_signal(symbol)

            if result['status'] == 'success':
                results['signals'][symbol] = result['signal']
                results['summary']['successful'] += 1
            elif result['status'] == 'no_signal':
                results['summary']['no_signal'] += 1
            else:
                results['summary']['failed'] += 1
                results['signals'][symbol] = result

        return results

    def get_last_signal(self, symbol: str) -> Optional[Dict]:
        """Get the last generated signal for a symbol (from cache)"""
        return self.last_generated_signals.get(symbol)

    def _save_signal_to_db(self, symbol: str, signal: Dict) -> None:
        """Save signal to database with full metadata"""
        try:
            # Extract signal details
            direction = signal.get('direction', 'WAIT')
            entry = signal.get('entry', 0)
            target = signal.get('target', 0)
            stop_loss = signal.get('stop_loss', 0)
            confidence = signal.get('confidence', 0)

            # Create database signal
            db_signal = Signal(
                symbol=symbol,
                entry=entry,
                sl=stop_loss,
                target=target,
                verdict=direction,
                timestamp=datetime.utcnow(),
                status='PENDING',
                # Additional fields (if Signal model supports)
                confidence=confidence,
                setup=signal.get('setup', ''),
                ema_signal=signal.get('trend', ''),
                oi_bias=signal.get('oi_skew', ''),
                pcr=signal.get('analysis', {}).get('pcr', 0),
                quality_score=json.dumps(signal.get('quality_score', {})),
                reasoning=json.dumps(signal.get('reasons', []))
            )

            # Save to database
            from user_model import SessionLocal
            db = SessionLocal()
            db.add(db_signal)
            db.commit()
            db.close()

        except Exception as e:
            logger.error(f"Warning: Could not save signal to database: {str(e)}")

    def _generate_consistency_marker(self, symbol: str, signal: Dict) -> str:
        """
        Generate a consistency marker to verify identical signals across clients.
        Hash based on key signal parameters.
        """
        try:
            marker_data = f"{symbol}:{signal.get('direction')}:{signal.get('entry')}:{signal.get('target')}:{signal.get('stop_loss')}:{signal.get('confidence')}"
            import hashlib
            return hashlib.md5(marker_data.encode()).hexdigest()[:8]
        except:
            return 'UNKNOWN'

    def validate_signal_consistency(self, symbol: str, external_signal: Dict) -> Dict:
        """
        Validate that an external signal matches what System B would generate.
        Used to verify dashboard/terminal consistency.
        """
        # Generate signal locally
        local_signal = self.get_last_signal(symbol)

        if not local_signal:
            return {
                'consistent': False,
                'reason': 'No local signal to compare'
            }

        # Compare key fields
        differences = {}

        for field in ['direction', 'entry', 'target', 'stop_loss', 'confidence']:
            local_val = local_signal.get(field)
            external_val = external_signal.get(field)

            if local_val != external_val:
                differences[field] = {
                    'local': local_val,
                    'external': external_val,
                    'match': False
                }

        return {
            'consistent': len(differences) == 0,
            'differences': differences,
            'timestamp': datetime.utcnow().isoformat()
        }

    def get_signal_history(self, symbol: str, limit: int = 20) -> List[Dict]:
        """
        Get recent signal history for a symbol.
        """
        try:
            from user_model import SessionLocal
            from sqlalchemy import desc

            db = SessionLocal()
            signals = db.query(Signal).filter(
                Signal.symbol == symbol
            ).order_by(desc(Signal.timestamp)).limit(limit).all()

            db.close()

            return [self._signal_to_dict(s) for s in signals]

        except Exception as e:
            logger.error(f"Error fetching signal history: {str(e)}")
            return []

    def get_signal_performance(self, symbol: str = None) -> Dict:
        """
        Calculate performance metrics for signals.
        """
        try:
            from user_model import SessionLocal
            from sqlalchemy import func

            db = SessionLocal()

            if symbol:
                signals = db.query(Signal).filter(Signal.symbol == symbol).all()
            else:
                signals = db.query(Signal).all()

            db.close()

            # Calculate metrics
            total = len(signals)
            executed = sum(1 for s in signals if s.status == 'EXECUTED')
            pending = sum(1 for s in signals if s.status == 'PENDING')

            # P&L calculation (would need execution price data)
            winning_trades = sum(1 for s in signals if hasattr(s, 'pnl') and s.pnl > 0)
            losing_trades = sum(1 for s in signals if hasattr(s, 'pnl') and s.pnl < 0)

            win_rate = (winning_trades / (winning_trades + losing_trades) * 100
                       if (winning_trades + losing_trades) > 0 else 0)

            return {
                'symbol': symbol or 'ALL',
                'total_signals': total,
                'executed': executed,
                'pending': pending,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error calculating performance: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    @staticmethod
    def _signal_to_dict(signal: Signal) -> Dict:
        """Convert Signal model to dictionary"""
        return {
            'id': signal.id,
            'symbol': signal.symbol,
            'entry': signal.entry,
            'target': signal.target,
            'stop_loss': signal.sl,
            'direction': signal.verdict,
            'confidence': getattr(signal, 'confidence', 0),
            'timestamp': signal.timestamp.isoformat() if signal.timestamp else None,
            'status': signal.status,
            'setup': getattr(signal, 'setup', ''),
            'trend': getattr(signal, 'ema_signal', '')
        }


# Global instance
_unified_signal_service = None


def get_unified_signal_service(market_data: Optional[AngelOneMarketData] = None) -> UnifiedSignalService:
    """Get or create global signal service instance"""
    global _unified_signal_service

    if _unified_signal_service is None:
        _unified_signal_service = UnifiedSignalService(market_data)

    return _unified_signal_service


def reset_signal_service():
    """Reset global service instance (for testing)"""
    global _unified_signal_service
    _unified_signal_service = None
