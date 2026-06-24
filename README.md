# 🚀 Tradosphere V3.1 - AI-Powered Trading Platform

Advanced multi-tenant SaaS trading platform with Angel One broker integration, AI analysis, and paper trading.

## ✨ Features

### Phase 1: Authentication & Multi-Tenancy ✅
- Email/Password + Google OAuth login
- JWT token management (access + refresh)
- Multi-tenant data isolation
- API key management

### Phase 2: SaaS Features ✅
- Subscription management (Free/Pro/Enterprise)
- Stripe payment integration
- Email notifications (SendGrid)
- Usage analytics & admin panel

### Phase 3: Trading ✅
- Live market prices (NIFTY, BANKNIFTY)
- Technical analysis (EMA, RSI, MACD)
- Options chain with Greeks calculator
- Paper trading system
- Signal generation
- Claude AI-powered insights

## 🚀 Quick Start

### Local Development
```bash
# 1. Install dependencies
pip install -r config/requirements.txt

# 2. Set up environment
cp .env.example .env.development
# Edit .env.development with your credentials

# 3. Initialize database
cd backend
python3 db_init_v3_1.py

# 4. Run server
python3 tradosphere_saas_server_v3_1.py

# 5. Open browser
# http://localhost:5001/login
# Demo: demo@tradosphere.com / DemoPass@2024
```

### Production Deployment (Railway)
```bash
1. Push code to GitHub
2. Connect Railway to repository
3. Set environment variables in Railway dashboard
4. Deploy
```

## 📁 Project Structure

```
tradosphere_v3.1/
├── backend/
│   ├── tradosphere_saas_server_v3_1.py    # Main Flask app
│   ├── auth_routes_v3_1.py                # Auth endpoints
│   ├── trading_routes_v3_1.py             # Trading endpoints
│   ├── billing_routes_v3_1.py             # Billing endpoints
│   ├── greeks_calculator.py               # Options Greeks
│   ├── claude_ai_service.py               # Claude AI integration
│   ├── market_data.py                     # Angel One integration
│   └── requirements.txt
├── frontend/
│   ├── login_v3.1.html                   # Login page
│   ├── dashboard_live_v3.1.html           # Dashboard
│   ├── config.js                          # API configuration
│   └── api-client.js                      # API client
└── docs/
    └── API_SPEC.md                        # API documentation
```

## 🔐 Security

- JWT token-based authentication
- Multi-tenant data isolation
- SQL injection protection (SQLAlchemy)
- Environment variable secrets (no hardcoding)
- HTTPS/TLS ready

## 📊 API Endpoints

### Authentication
- `POST /api/auth/login` - Email/password login
- `POST /api/auth/signup` - User registration
- `POST /api/auth/google` - Google OAuth
- `GET /api/auth/me` - Current user

### Trading
- `GET /api/market/live` - Live prices
- `GET /api/analysis/technical` - Technical analysis
- `GET /api/analysis/options` - Options chain
- `POST /api/analysis/ai-insights` - AI analysis

### Paper Trading
- `GET /api/trading/open-trades` - Open positions
- `POST /api/trading/open-trade` - Create trade
- `POST /api/trading/close-trade` - Close trade

## 🤝 Contributing

1. Clone repository
2. Create feature branch
3. Make changes
4. Test locally
5. Push to GitHub
6. Create pull request

## 📝 License

Proprietary - All rights reserved

## 👤 Author

Tradosphere Development Team

---

**Status**: Production Ready ✅
**Version**: 3.1
**Last Updated**: June 24, 2026
