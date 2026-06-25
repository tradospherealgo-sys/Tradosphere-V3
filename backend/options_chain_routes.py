"""
Flask Routes for Options Chain Data
API endpoints for options chain analysis, Greeks, and smart money analysis
"""

from flask import Blueprint, request, jsonify
from functools import wraps
from logger_config import get_logger
from options_chain import OptionsChain
from angel_one_options_handler import AngelOneOptionsHandler

logger = get_logger(__name__)

# Create blueprint
options_routes = Blueprint('options', __name__, url_prefix='/api/options')


def require_params(*params):
    """Decorator to validate required parameters"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            for param in params:
                if param not in request.json or request.json[param] is None:
                    return jsonify({'error': f'Missing required parameter: {param}'}), 400
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@options_routes.route('/chain', methods=['POST'])
@require_params('symbol', 'spot_price', 'expiry_date', 'smartapi_client')
def get_options_chain():
    """
    Fetch and analyze LIVE options chain from Angel One

    Request:
    {
        "symbol": "NIFTY50",
        "spot_price": 23450.25,
        "expiry_date": "25JUN2026",
        "expiry_days": 7,
        "smartapi_client": <SmartConnect instance>
    }

    Response:
    {
        "symbol": "NIFTY50",
        "spot_price": 23450.25,
        "timestamp": "2026-06-25T10:30:00",
        "source": "Angel One SmartAPI (LIVE)",
        "chain_summary": {...},
        "oi_analysis": {...},
        "expected_move": {...},
        "skew": {...}
    }
    """
    try:
        data = request.json
        symbol = data['symbol']
        spot_price = float(data['spot_price'])
        expiry_date = data['expiry_date']
        expiry_days = data.get('expiry_days', 7)
        smartapi_client = data.get('smartapi_client')

        if not smartapi_client:
            return jsonify({'error': '❌ SmartAPI client required - LIVE data only, no mocks'}), 400

        # Create handler with REAL client
        handler = AngelOneOptionsHandler(smartapi_client, symbol, expiry_date)

        # Fetch LIVE chain from Angel One
        chain_response = handler.fetch_options_chain(spot_price)

        if not chain_response.get('fetched'):
            logger.error(f"❌ Failed to fetch LIVE options chain for {symbol}")
            return jsonify({
                'error': 'Failed to fetch live options chain from Angel One',
                'details': chain_response.get('error', 'Unknown error')
            }), 500

        # Analyze chain
        analysis = handler.parse_chain_and_analyze(chain_response, expiry_days)

        if 'error' in analysis:
            return jsonify(analysis), 400

        num_strikes = len(analysis.get('chain_summary', {}).get('atm_options', {}).get('options', []))
        logger.info(f"✅ LIVE OPTIONS CHAIN ANALYZED: {symbol} | {num_strikes} strikes | Source: Angel One SmartAPI")

        return jsonify({
            'status': 'success',
            'source': 'Angel One SmartAPI (LIVE)',
            'data': analysis
        }), 200

    except Exception as e:
        logger.error(f"❌ Error in GET /chain: {str(e)}")
        return jsonify({'error': str(e)}), 500


@options_routes.route('/iv-rank', methods=['POST'])
@require_params('symbol', 'current_iv', 'historical_iv')
def get_iv_rank():
    """
    Calculate IV Rank and Percentile

    Request:
    {
        "symbol": "NIFTY50",
        "current_iv": 18.5,
        "historical_iv": [15.2, 16.1, 17.3, ...]
    }
    """
    try:
        data = request.json
        symbol = data['symbol']
        current_iv = float(data['current_iv'])
        historical_iv = [float(x) for x in data['historical_iv']]

        # Create chain instance
        chain = OptionsChain(spot_price=23450, symbol=symbol)

        # Calculate IV rank
        result = chain.calculate_iv_rank_percentile(historical_iv, current_iv)

        logger.info(f"✅ IV Rank calculated: {symbol} | Rank={result.get('iv_rank')}%")

        return jsonify({
            'status': 'success',
            'symbol': symbol,
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"❌ Error in GET /iv-rank: {str(e)}")
        return jsonify({'error': str(e)}), 500


@options_routes.route('/expected-move', methods=['POST'])
@require_params('symbol', 'spot_price', 'current_iv', 'expiry_days')
def get_expected_move():
    """
    Calculate expected move (1 standard deviation)

    Request:
    {
        "symbol": "NIFTY50",
        "spot_price": 23450.25,
        "current_iv": 18.5,
        "expiry_days": 7
    }
    """
    try:
        data = request.json
        symbol = data['symbol']
        spot_price = float(data['spot_price'])
        current_iv = float(data['current_iv']) / 100.0  # Convert percentage to decimal
        expiry_days = int(data['expiry_days'])

        # Create chain instance
        chain = OptionsChain(spot_price, symbol, expiry_days)

        # Calculate expected move
        result = chain.calculate_expected_move_for_stock()

        logger.info(f"✅ Expected move calculated: {symbol} | Move=${result['expected_move_dollar']:.2f}")

        return jsonify({
            'status': 'success',
            'symbol': symbol,
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"❌ Error in GET /expected-move: {str(e)}")
        return jsonify({'error': str(e)}), 500


@options_routes.route('/greeks-ladder', methods=['POST'])
@require_params('symbol', 'spot_price', 'num_strikes')
def get_greeks_ladder():
    """
    Get Greeks ladder for visualization

    Request:
    {
        "symbol": "NIFTY50",
        "spot_price": 23450.25,
        "num_strikes": 9,
        "expiry_days": 7,
        "chain_data": {...}
    }
    """
    try:
        data = request.json
        symbol = data['symbol']
        spot_price = float(data['spot_price'])
        num_strikes = int(data['num_strikes'])
        expiry_days = data.get('expiry_days', 7)
        chain_data = data.get('chain_data', {})

        # Create chain instance
        chain = OptionsChain(spot_price, symbol, expiry_days)

        # Parse chain if provided
        if chain_data and 'fetched' in chain_data:
            chain.parse_chain_from_smartapi(chain_data)

        # Build ladder
        result = chain.build_greeks_ladder()

        if 'error' in result:
            return jsonify(result), 400

        logger.info(f"✅ Greeks ladder built: {symbol} | {len(result.get('ladder', []))} strikes")

        return jsonify({
            'status': 'success',
            'symbol': symbol,
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"❌ Error in GET /greeks-ladder: {str(e)}")
        return jsonify({'error': str(e)}), 500


@options_routes.route('/portfolio-greeks', methods=['POST'])
@require_params('symbol', 'positions')
def get_portfolio_greeks():
    """
    Calculate Greeks aggregation for portfolio

    Request:
    {
        "symbol": "NIFTY50",
        "spot_price": 23450.25,
        "positions": [
            {"strike": 23000, "type": "CALL", "quantity": 2, "price": 450},
            {"strike": 23500, "type": "PUT", "quantity": -1, "price": 42}
        ]
    }
    """
    try:
        data = request.json
        symbol = data['symbol']
        spot_price = float(data.get('spot_price', 23450))
        positions = data['positions']

        # Create chain instance
        chain = OptionsChain(spot_price, symbol)

        # Parse chain if provided
        if 'chain_data' in data:
            chain.parse_chain_from_smartapi(data['chain_data'])

        # Calculate portfolio Greeks
        result = chain.calculate_portfolio_greeks(positions)

        if 'error' in result:
            return jsonify(result), 400

        logger.info(f"✅ Portfolio Greeks calculated: {symbol} | {len(positions)} positions")

        return jsonify({
            'status': 'success',
            'symbol': symbol,
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"❌ Error in GET /portfolio-greeks: {str(e)}")
        return jsonify({'error': str(e)}), 500


@options_routes.route('/skew-analysis', methods=['POST'])
@require_params('symbol', 'spot_price')
def get_skew_analysis():
    """
    Analyze IV skew across strikes

    Request:
    {
        "symbol": "NIFTY50",
        "spot_price": 23450.25,
        "chain_data": {...}
    }
    """
    try:
        data = request.json
        symbol = data['symbol']
        spot_price = float(data['spot_price'])
        chain_data = data.get('chain_data', {})

        # Create chain instance
        chain = OptionsChain(spot_price, symbol)

        # Parse chain
        if chain_data and 'fetched' in chain_data:
            chain.parse_chain_from_smartapi(chain_data)

        # Analyze skew
        result = chain.analyze_skew()

        if 'error' in result:
            return jsonify(result), 400

        logger.info(f"✅ Skew analysis: {symbol} | Direction={result.get('skew_direction')}")

        return jsonify({
            'status': 'success',
            'symbol': symbol,
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"❌ Error in GET /skew-analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500


@options_routes.route('/health', methods=['GET'])
def options_health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'module': 'options-chain',
        'version': '1.0.0',
        'timestamp': __import__('datetime').datetime.now().isoformat()
    }), 200
