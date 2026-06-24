"""
Graceful Degradation Module

Ensures Tradosphere continues running even when:
- Angel One broker is unavailable
- Market data feeds fail
- Option chain is unavailable
- Backend components fail

Frontend receives "degraded" status responses with fallback data.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class GracefulDegradation:
    """Handle component failures gracefully"""

    def __init__(self):
        self.broker_available = True
        self.market_data_available = True
        self.option_chain_available = True
        self.database_available = True
        self.signal_engine_available = True

    def mark_broker_failed(self, reason: str):
        """Mark broker as unavailable"""
        self.broker_available = False
        logger.warning(f"Broker marked as unavailable: {reason}")

    def mark_broker_healthy(self):
        """Mark broker as available"""
        self.broker_available = True

    def mark_market_data_failed(self, reason: str):
        """Mark market data as unavailable"""
        self.market_data_available = False
        logger.warning(f"Market data marked as unavailable: {reason}")

    def mark_option_chain_failed(self, reason: str):
        """Mark option chain as unavailable"""
        self.option_chain_available = False
        logger.warning(f"Option chain marked as unavailable: {reason}")

    def is_degraded(self) -> bool:
        """Check if system is in degraded mode"""
        return not all([
            self.broker_available,
            self.market_data_available,
            self.database_available,
            self.signal_engine_available
        ])

    def get_degradation_status(self) -> Dict:
        """Get current degradation status"""
        return {
            'degraded': self.is_degraded(),
            'components': {
                'broker': 'available' if self.broker_available else 'unavailable',
                'market_data': 'available' if self.market_data_available else 'unavailable',
                'option_chain': 'available' if self.option_chain_available else 'unavailable',
                'database': 'available' if self.database_available else 'unavailable',
                'signal_engine': 'available' if self.signal_engine_available else 'unavailable'
            }
        }

    def handle_broker_error(self, error: Exception):
        """Handle broker errors"""
        logger.error(f"Broker error: {error}")
        self.mark_broker_failed(str(error))
        
        # Could emit alert here
        return {
            'status': 'degraded',
            'message': 'Broker connection failed, using cached data',
            'component': 'broker'
        }

    def handle_market_data_error(self, error: Exception):
        """Handle market data errors"""
        logger.error(f"Market data error: {error}")
        self.mark_market_data_failed(str(error))
        
        return {
            'status': 'degraded',
            'message': 'Market data unavailable',
            'component': 'market_data'
        }

    def handle_api_timeout(self, endpoint: str):
        """Handle API timeouts"""
        logger.warning(f"API timeout on {endpoint}")
        
        return {
            'status': 'error',
            'message': f'Request timeout: {endpoint}',
            'component': 'api'
        }


# Global degradation handler
_degradation_handler: Optional[GracefulDegradation] = None


def get_degradation_handler() -> GracefulDegradation:
    """Get or create degradation handler"""
    global _degradation_handler
    if _degradation_handler is None:
        _degradation_handler = GracefulDegradation()
    return _degradation_handler


def initialize_degradation_handling():
    """Initialize degradation handling"""
    return get_degradation_handler()
