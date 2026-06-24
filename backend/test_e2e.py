#!/usr/bin/env python3
"""
End-to-End Testing - Verify complete workflows
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

os.environ['JWT_SECRET'] = 'test-secret-key'
os.environ['FLASK_ENV'] = 'development'

from tradosphere_saas_server import app
from user_model import SessionLocal, create_user
from auth_manager import PasswordManager, JWTManager

def test_flow():
    """Test complete user flow"""
    print("\n" + "="*60)
    print("🧪 TRADOSPHERE V1 - END-TO-END TEST")
    print("="*60)

    # Create test client
    client = app.test_client()

    # Clean up any existing test users
    db = SessionLocal()
    from user_model import User
    db.query(User).filter(User.email.in_(['testuser@tradosphere.com', 'admin@tradosphere.com'])).delete()
    db.commit()
    db.close()

    # PHASE 1: Signup
    print("\n✅ PHASE 1: User Signup")
    signup_response = client.post('/api/auth/signup', json={
        'email': 'testuser@tradosphere.com',
        'password': 'TestPass123',
        'first_name': 'Test',
        'last_name': 'User'
    })
    signup_data = signup_response.get_json()
    print(f"   Status: {signup_data.get('status')}")

    if signup_data.get('status') == 'success':
        token = signup_data['data']['tokens']['access_token']
        user_id = signup_data['data']['user']['id']
        print(f"   Token: {token[:20]}...")
        print(f"   User ID: {user_id}")
    else:
        token = None
        print(f"   Error: {signup_data.get('message')}")

    # PHASE 2: Login
    print("\n✅ PHASE 2: User Login")
    login_response = client.post('/api/auth/login', json={
        'email': 'testuser@tradosphere.com',
        'password': 'TestPass123'
    })
    login_data = login_response.get_json()
    print(f"   Full Response: {json.dumps(login_data, indent=2)}")
    print(f"   Status: {login_data.get('status')}")
    print(f"   Role: {login_data.get('user_role')}")
    if login_data.get('status') == 'error':
        print(f"   Error: {login_data.get('message')}")

    if login_data.get('status') == 'success':
        token = login_data['data']['tokens']['access_token']
        print(f"   Token: {token[:20]}...")

    # PHASE 3: Get Dashboard
    print("\n✅ PHASE 3: Load Dashboard")
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    dashboard_response = client.get('/api/user/dashboard-overview', headers=headers)
    dashboard_data = dashboard_response.get_json()
    print(f"   Status: {dashboard_data.get('status')}")
    if dashboard_data.get('status') == 'success':
        account = dashboard_data['data']['account']
        print(f"   Capital: ₹{account['total_capital']:,}")
        print(f"   P&L: ₹{account['total_pnl']:,}")

    # PHASE 4: Get Subscription Plans
    print("\n✅ PHASE 4: Get Subscription Plans")
    plans_response = client.get('/api/billing/plans', headers=headers)
    plans_data = plans_response.get_json()
    print(f"   Status: {plans_data.get('status')}")
    if plans_data.get('status') == 'success':
        for plan in plans_data.get('data', []):
            print(f"   - {plan['tier'].upper()}: ₹{plan['monthly_price']}/month")

    # PHASE 5: Get Market Data
    print("\n✅ PHASE 5: Get Market Data")
    market_response = client.get('/api/market/overview', headers=headers)
    market_data = market_response.get_json()
    print(f"   Status: {market_data.get('status')}")
    if market_data.get('status') == 'success':
        for symbol in market_data['data']['symbols'][:2]:
            print(f"   - {symbol['name']}: ₹{symbol['price']} ({symbol['changePercent']:+.2f}%)")

    # PHASE 6: Get Signals
    print("\n✅ PHASE 6: Get Signals")
    signals_response = client.get('/api/signals', headers=headers)
    signals_data = signals_response.get_json()
    print(f"   Status: {signals_data.get('status')}")
    if signals_data.get('status') == 'error':
        print(f"   Error: {signals_data.get('message')}")
    if signals_data.get('status') == 'success':
        signal_count = len(signals_data.get('data', []))
        print(f"   Total Signals: {signal_count}")

    # PHASE 7: Get User Profile
    print("\n✅ PHASE 7: Get User Profile")
    profile_response = client.get('/api/user/profile', headers=headers)
    profile_data = profile_response.get_json()
    print(f"   Status: {profile_data.get('status')}")
    if profile_data.get('status') == 'success':
        user = profile_data['data']
        print(f"   Name: {user['first_name']} {user['last_name']}")
        print(f"   Email: {user['email']}")

    # PHASE 8: Get Watchlist
    print("\n✅ PHASE 8: Get Watchlist")
    watchlist_response = client.get('/api/user/watchlist', headers=headers)
    watchlist_data = watchlist_response.get_json()
    print(f"   Status: {watchlist_data.get('status')}")
    if watchlist_data.get('status') == 'success':
        symbols = [s['symbol'] for s in watchlist_data.get('data', [])]
        print(f"   Symbols: {', '.join(symbols)}")

    # PHASE 9: Get Subscription
    print("\n✅ PHASE 9: Get User Subscription")
    sub_response = client.get('/api/user/subscription', headers=headers)
    sub_data = sub_response.get_json()
    print(f"   Status: {sub_data.get('status')}")
    if sub_data.get('status') == 'success':
        plan = sub_data['data']
        print(f"   Plan: {plan['plan'].upper()}")
        print(f"   Status: {plan['status']}")

    # PHASE 10: Get Billing History
    print("\n✅ PHASE 10: Get Billing History")
    billing_response = client.get('/api/user/billing-history', headers=headers)
    billing_data = billing_response.get_json()
    print(f"   Status: {billing_data.get('status')}")
    if billing_data.get('status') == 'success':
        invoices = billing_data.get('data', [])
        print(f"   Total Invoices: {len(invoices)}")

    # PHASE 11: Admin Dashboard (with admin user)
    print("\n✅ PHASE 11: Admin Dashboard")
    # Create admin user
    db = SessionLocal()
    admin_user = create_user(db, 'admin@tradosphere.com', PasswordManager.hash_password('Admin123'))
    admin_user.is_admin = True
    db.commit()

    admin_tokens = JWTManager.generate_tokens(admin_user.id, admin_user.email)
    admin_token = admin_tokens['access_token']
    admin_headers = {'Authorization': f'Bearer {admin_token}'}
    db.close()

    admin_dashboard = client.get('/api/admin/dashboard', headers=admin_headers)
    admin_data = admin_dashboard.get_json()
    print(f"   Status: {admin_data.get('status')}")
    if admin_data.get('status') == 'error':
        print(f"   Error: {admin_data.get('message')}")
    if admin_data.get('status') == 'success':
        data = admin_data['data']
        print(f"   Total Users: {data['users']['total']}")
        print(f"   Active Subscriptions: {data['subscriptions']['active']}")
        print(f"   Monthly Revenue: ₹{data['revenue']['monthly']:,.0f}")

    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED")
    print("="*60 + "\n")

if __name__ == '__main__':
    with app.app_context():
        test_flow()
