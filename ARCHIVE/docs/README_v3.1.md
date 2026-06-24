# Tradosphere V3.1 - Trading Intelligence Platform

**Status:** Production Ready (Live Testing Phase)

## Features

✅ **Authentication**
- Manual login (email/password)
- Google OAuth integration
- JWT token-based sessions

✅ **Trading Dashboard**
- Live market prices (NIFTY, BANKNIFTY, etc.)
- Options chain data
- Technical analysis charts
- Dashboard overview stats (P&L, portfolio value)
- Paper trading stats & open trades
- AI insights tab
- Trade generation & management

## Project Structure

```
tradosphere_v3.1/
├── frontend/                 # Frontend HTML files
│   ├── login_v3.1.html      # Login page (manual + Google OAuth)
│   └── dashboard_live_v3.1.html  # Main trading dashboard
├── backend/                  # Python backend files
│   ├── tradosphere_saas_server_v3.1.py  # Main Flask server
│   ├── auth_routes_v3.1.py              # Authentication endpoints
│   ├── trading_routes_v3.1.py           # Paper trading endpoints
│   ├── user_routes_v3.1.py              # User profile endpoints
│   ├── admin_routes_v3.1.py             # Admin panel endpoints
│   ├── billing_routes_v3.1.py           # Subscription endpoints
│   ├── auth_manager_v3.1.py             # Password & JWT management
│   ├── database_v3.1.py                 # Database models & ORM
│   ├── user_model_v3.1.py               # User database model
│   ├── paper_trading_model_v3.1.py      # Paper trading models
│   └── db_init_v3.1.py                  # Database initialization
├── config/                   # Configuration files
│   ├── config_v3.1.js        # Frontend API configuration
│   ├── .env.example          # Environment variables template
│   └── requirements.txt       # Python dependencies
└── docs/
    └── README_v3.1.md        # This file
```

## Setup & Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/tradosphere-v3.1.git
cd tradosphere_v3.1
```

### 2. Install Dependencies
```bash
pip install -r config/requirements.txt
```

### 3. Configure Environment
```bash
cp config/.env.example .env
# Edit .env with your settings
```

### 4. Initialize Database
```bash
JWT_SECRET="your-secret-key" python backend/db_init_v3.1.py
```

### 5. Start Server
```bash
PORT=5001 JWT_SECRET="your-secret-key" python backend/tradosphere_saas_server_v3.1.py
```

### 6. Access Application
- **Login:** http://localhost:5001/login
- **Dashboard:** http://localhost:5001/user/dashboard (after login)

## Test Credentials

```
Email: demo@tradosphere.com
Password: DemoPass@2024
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - Manual login
- `POST /api/auth/google` - Google OAuth
- `POST /api/auth/logout` - Logout

### Trading
- `GET /api/market/live` - Live market prices
- `GET /api/analysis/options` - Options chain data
- `GET /api/analysis/technical` - Technical analysis
- `POST /api/trading/create-trade` - Create paper trade

### User
- `GET /api/user/profile` - User profile
- `GET /api/user/dashboard-overview` - Dashboard stats

### Paper Trading
- `GET /api/trading/open-trades` - Open trades
- `GET /api/trading/closed-trades` - Closed trades
- `GET /api/trading/stats` - Trading statistics

## Database Models

### Users
- User authentication & profiles
- API key management
- Subscription tracking

### Paper Trading
- Virtual accounts (₹100,000 initial capital)
- Trade execution & management
- P&L tracking
- Performance analytics

## Security

- JWT token-based authentication
- Password hashing with salt
- CORS enabled for frontend
- Environment-based configuration
- SQL injection prevention via ORM

## Development Notes

- **Frontend:** Vanilla JavaScript (no framework)
- **Backend:** Flask with SQLAlchemy ORM
- **Database:** SQLite (dev), PostgreSQL (production)
- **Authentication:** JWT tokens + refresh tokens
- **API:** RESTful design

## Testing Checklist

- [ ] Login works (manual + Google)
- [ ] Dashboard loads with live data
- [ ] Options chain displays
- [ ] Technical analysis charts render
- [ ] Paper trades can be created
- [ ] Dashboard stats update in real-time
- [ ] Trade history displays correctly

## Known Limitations

- Google OAuth requires Google Cloud Console setup
- Angel One API requires active credentials
- Email notifications need SendGrid API key
- Live market data depends on market connectivity

## Next Stages

**Stage 2 - Enhancement:**
- Real trade execution
- Advanced charting (TradingView integration)
- Mobile app
- Automated strategies

## Support & Issues

Report issues on GitHub: [tradosphere-v3.1/issues](https://github.com/yourusername/tradosphere-v3.1/issues)

---

**Version:** 3.1  
**Last Updated:** June 24, 2026  
**Status:** Production Ready
