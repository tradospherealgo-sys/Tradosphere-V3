"""
Health Check Module - Production Deployment

Provides comprehensive health status of all critical systems:
- Database connectivity
- Broker connection (Angel One)
- Market data feeds
- Signal generation engine
- API connectivity
"""

from datetime import datetime
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class HealthChecker:
    """Check health of all system components"""

    def __init__(self):
        self.start_time = datetime.utcnow()
        self.status_cache = {}

    def check_database(self) -> Dict:
        """Check database connectivity and schema"""
        try:
            from database import engine, Signal, Base
            from sqlalchemy import inspect, text

            # Test connection
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                if not result:
                    return {
                        'status': 'unhealthy',
                        'message': 'Cannot execute query',
                        'timestamp': datetime.utcnow().isoformat()
                    }

            # Check schema
            inspector = inspect(engine)
            tables = inspector.get_table_names()

            if 'signals' not in tables:
                return {
                    'status': 'unhealthy',
                    'message': 'Signals table not found',
                    'timestamp': datetime.utcnow().isoformat()
                }

            columns = inspector.get_columns('signals')
            column_count = len(columns)
            expected_count = 19

            if column_count != expected_count:
                return {
                    'status': 'degraded',
                    'message': f'Schema mismatch: {column_count} columns, expected {expected_count}',
                    'columns': column_count,
                    'expected': expected_count,
                    'timestamp': datetime.utcnow().isoformat()
                }

            return {
                'status': 'healthy',
                'database': 'connected',
                'tables': len(tables),
                'signal_columns': column_count,
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    def check_broker(self) -> Dict:
        """Check Angel One broker connection"""
        try:
            from market_data import AngelOneMarketData

            market = AngelOneMarketData()

            # Try to get price (this tests auth + connectivity)
            nifty = market.get_nifty_price()

            if nifty and nifty.get('ltp'):
                return {
                    'status': 'healthy',
                    'broker': 'Angel One',
                    'authenticated': True,
                    'last_price': nifty.get('ltp'),
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                return {
                    'status': 'degraded',
                    'broker': 'Angel One',
                    'authenticated': True,
                    'message': 'Connected but no market data',
                    'timestamp': datetime.utcnow().isoformat()
                }

        except Exception as e:
            logger.warning(f"Broker health check failed: {e}")
            return {
                'status': 'unhealthy',
                'broker': 'Angel One',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    def check_signal_engine(self) -> Dict:
        """Check signal generation engine"""
        try:
            from signal_writer import SignalGenerator
            from unified_signal_service import get_unified_signal_service

            # Check System B
            generator = SignalGenerator(None)
            service = get_unified_signal_service(None)

            if hasattr(generator, 'generate_signals') and hasattr(service, 'generate_signal'):
                return {
                    'status': 'healthy',
                    'engine': 'System B (SignalGenerator)',
                    'methods': ['generate_signals', 'generate_signal'],
                    'unified_service': 'active',
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                return {
                    'status': 'unhealthy',
                    'engine': 'System B',
                    'message': 'Missing required methods',
                    'timestamp': datetime.utcnow().isoformat()
                }

        except Exception as e:
            logger.error(f"Signal engine health check failed: {e}")
            return {
                'status': 'unhealthy',
                'engine': 'System B',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    def check_market_data(self) -> Dict:
        """Check market data feed status"""
        try:
            from market_data import AngelOneMarketData

            market = AngelOneMarketData()

            # Check NIFTY
            nifty = market.get_nifty_price()
            # Check BANKNIFTY
            bnf = market.get_banknifty_price()
            # Check option chain
            opt_chain = market.get_option_chain('NIFTY')

            feeds = {
                'nifty': bool(nifty and nifty.get('ltp')),
                'banknifty': bool(bnf and bnf.get('ltp')),
                'option_chain': bool(opt_chain and len(opt_chain) > 0)
            }

            healthy_count = sum(1 for v in feeds.values() if v)

            if healthy_count == 3:
                status = 'healthy'
            elif healthy_count >= 1:
                status = 'degraded'
            else:
                status = 'unhealthy'

            return {
                'status': status,
                'feeds': feeds,
                'healthy_feeds': healthy_count,
                'total_feeds': len(feeds),
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.warning(f"Market data health check failed: {e}")
            return {
                'status': 'unhealthy',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    def get_overall_health(self) -> Dict:
        """Get overall system health"""
        db_health = self.check_database()
        broker_health = self.check_broker()
        engine_health = self.check_signal_engine()
        market_health = self.check_market_data()

        # Determine overall status
        statuses = [
            db_health.get('status'),
            broker_health.get('status'),
            engine_health.get('status'),
            market_health.get('status')
        ]

        if all(s == 'healthy' for s in statuses):
            overall_status = 'healthy'
        elif 'unhealthy' in statuses:
            overall_status = 'unhealthy'
        else:
            overall_status = 'degraded'

        uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'uptime_seconds': int(uptime_seconds),
            'components': {
                'database': db_health,
                'broker': broker_health,
                'signal_engine': engine_health,
                'market_data': market_health
            },
            'version': '1.0.0',
            'environment': 'production'
        }

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON response"""
        return self.get_overall_health()


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get or create health checker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def initialize_health_check():
    """Initialize health checker"""
    return get_health_checker()
