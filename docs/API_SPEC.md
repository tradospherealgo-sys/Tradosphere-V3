# Tradosphere V3.1 - API Specification

## Standard Response Format

All API endpoints return JSON in this format:

### Success Response
```json
{
  "status": "success",
  "data": { ... },
  "error": null,
  "timestamp": "2026-06-24T15:30:00Z"
}
```

### Error Response
```json
{
  "status": "error",
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message"
  },
  "timestamp": "2026-06-24T15:30:00Z"
}
```

---

## Authentication Endpoints

### POST /api/auth/login
**Description:** Manual email/password login
**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
**Response Success:**
```json
{
  "status": "success",
  "data": {
    "user_id": "uuid",
    "email": "user@example.com",
    "token": "jwt_token_here",
    "expires_in": 3600
  },
  "error": null
}
```

### POST /api/auth/google
**Description:** Google OAuth login
**Request:**
```json
{
  "code": "google_auth_code"
}
```
**Response Success:**
```json
{
  "status": "success",
  "data": {
    "user_id": "uuid",
    "email": "user@gmail.com",
    "token": "jwt_token",
    "expires_in": 3600
  },
  "error": null
}
```

### GET /api/auth/me
**Description:** Get current user info
**Headers:** `Authorization: Bearer <token>`
**Response Success:**
```json
{
  "status": "success",
  "data": {
    "user_id": "uuid",
    "email": "user@example.com",
    "username": "username",
    "created_at": "2026-06-24T10:00:00Z"
  },
  "error": null
}
```

---

## Market Data Endpoints

### GET /api/market/overview
**Description:** Get all major indices prices
**Headers:** `Authorization: Bearer <token>`
**Response Success:**
```json
{
  "status": "success",
  "data": {
    "symbols": [
      {
        "name": "NIFTY",
        "price": 24150.50,
        "change": 125.35,
        "changePercent": 0.52,
        "volume": 5000000,
        "openInterest": 1000000
      },
      {
        "name": "BANKNIFTY",
        "price": 51200.00,
        "change": 280.50,
        "changePercent": 0.55,
        "volume": 3000000,
        "openInterest": 500000
      }
    ],
    "timestamp": "2026-06-24T15:30:00Z"
  },
  "error": null
}
```

### GET /api/market/live
**Description:** Get live NIFTY and BANKNIFTY prices
**Headers:** `Authorization: Bearer <token>`
**Response Success:**
```json
{
  "status": "success",
  "data": {
    "NIFTY": {
      "price": 24150.50,
      "change": 125.35,
      "changePercent": 0.52,
      "high": 24200.00,
      "low": 24000.00,
      "open": 24100.00,
      "close": 24150.50,
      "timestamp": "2026-06-24T15:30:00Z"
    },
    "BANKNIFTY": {
      "price": 51200.00,
      "change": 280.50,
      "changePercent": 0.55,
      "high": 51500.00,
      "low": 51000.00,
      "open": 51100.00,
      "close": 51200.00,
      "timestamp": "2026-06-24T15:30:00Z"
    }
  },
  "error": null
}
```

---

## Trading Endpoints

### POST /api/trading/create-trade
**Description:** Create a new paper trade
**Headers:** `Authorization: Bearer <token>`
**Request:**
```json
{
  "symbol": "NIFTY",
  "quantity": 1,
  "entry_price": 24150.50,
  "stop_loss": 24000.00,
  "take_profit": 24300.00,
  "trade_type": "BUY"
}
```
**Response Success:**
```json
{
  "status": "success",
  "data": {
    "trade_id": "uuid",
    "symbol": "NIFTY",
    "quantity": 1,
    "entry_price": 24150.50,
    "current_price": 24150.50,
    "pnl": 0.00,
    "pnl_percent": 0.00,
    "status": "open",
    "created_at": "2026-06-24T15:30:00Z"
  },
  "error": null
}
```

### GET /api/trading/open-trades
**Description:** Get all open trades for user
**Headers:** `Authorization: Bearer <token>`
**Response Success:**
```json
{
  "status": "success",
  "data": {
    "trades": [
      {
        "trade_id": "uuid",
        "symbol": "NIFTY",
        "quantity": 1,
        "entry_price": 24150.50,
        "current_price": 24170.00,
        "pnl": 19.50,
        "pnl_percent": 0.08,
        "status": "open",
        "created_at": "2026-06-24T15:00:00Z"
      }
    ],
    "total_pnl": 19.50,
    "total_trades": 1
  },
  "error": null
}
```

### GET /api/trading/closed-trades
**Description:** Get all closed trades for user
**Headers:** `Authorization: Bearer <token>`
**Response Success:**
```json
{
  "status": "success",
  "data": {
    "trades": [
      {
        "trade_id": "uuid",
        "symbol": "BANKNIFTY",
        "quantity": 1,
        "entry_price": 51000.00,
        "exit_price": 51100.00,
        "pnl": 100.00,
        "pnl_percent": 0.196,
        "status": "closed",
        "created_at": "2026-06-24T14:00:00Z",
        "closed_at": "2026-06-24T15:00:00Z"
      }
    ],
    "total_pnl": 100.00,
    "total_trades": 1
  },
  "error": null
}
```

### GET /api/trading/stats
**Description:** Get trading statistics
**Headers:** `Authorization: Bearer <token>`
**Response Success:**
```json
{
  "status": "success",
  "data": {
    "total_trades": 10,
    "open_trades": 3,
    "closed_trades": 7,
    "winning_trades": 5,
    "losing_trades": 2,
    "win_rate": 71.43,
    "total_pnl": 5250.75,
    "max_gain": 500.00,
    "max_loss": -200.00,
    "avg_gain": 105.00,
    "avg_loss": -100.00
  },
  "error": null
}
```

---

## Analysis Endpoints

### GET /api/analysis/technical
**Description:** Get technical analysis for symbol
**Headers:** `Authorization: Bearer <token>`
**Query:** `?symbol=NIFTY`
**Response Success:**
```json
{
  "status": "success",
  "data": {
    "symbol": "NIFTY",
    "price": 24150.50,
    "indicators": {
      "rsi": 65.50,
      "macd": {
        "line": 45.30,
        "signal": 42.10,
        "histogram": 3.20
      },
      "bollinger_bands": {
        "upper": 24300.00,
        "middle": 24150.00,
        "lower": 24000.00
      },
      "sma_20": 24100.00,
      "sma_50": 24050.00,
      "ema_12": 24140.00,
      "ema_26": 24130.00
    },
    "signals": [
      "BUY_RSI",
      "BUY_MACD",
      "NEUTRAL_BB"
    ],
    "timestamp": "2026-06-24T15:30:00Z"
  },
  "error": null
}
```

### GET /api/analysis/options
**Description:** Get options chain for symbol
**Headers:** `Authorization: Bearer <token>`
**Query:** `?symbol=NIFTY&expiry=2026-06-28`
**Response Success:**
```json
{
  "status": "success",
  "data": {
    "symbol": "NIFTY",
    "spot_price": 24150.50,
    "chain": [
      {
        "strike": 24000,
        "call": {
          "price": 185.50,
          "bid": 184.00,
          "ask": 187.00,
          "iv": 18.50,
          "delta": 0.75,
          "gamma": 0.012,
          "theta": -0.05,
          "vega": 0.35
        },
        "put": {
          "price": 35.20,
          "bid": 34.50,
          "ask": 35.90,
          "iv": 17.80,
          "delta": -0.25,
          "gamma": 0.010,
          "theta": -0.02,
          "vega": 0.28
        }
      }
    ],
    "timestamp": "2026-06-24T15:30:00Z"
  },
  "error": null
}
```

---

## User Endpoints

### GET /api/user/profile
**Description:** Get user profile
**Headers:** `Authorization: Bearer <token>`
**Response Success:**
```json
{
  "status": "success",
  "data": {
    "user_id": "uuid",
    "email": "user@example.com",
    "username": "username",
    "first_name": "John",
    "last_name": "Doe",
    "profile_image": "url",
    "created_at": "2026-06-24T10:00:00Z",
    "updated_at": "2026-06-24T15:00:00Z"
  },
  "error": null
}
```

### GET /api/user/dashboard-overview
**Description:** Get dashboard overview stats
**Headers:** `Authorization: Bearer <token>`
**Response Success:**
```json
{
  "status": "success",
  "data": {
    "portfolio_value": 100000.00,
    "total_pnl": 5250.75,
    "pnl_percent": 5.25,
    "open_trades": 3,
    "open_pnl": 125.50,
    "available_balance": 89750.00,
    "used_margin": 10124.50
  },
  "error": null
}
```

---

## Error Response Examples

### 401 Unauthorized
```json
{
  "status": "error",
  "data": null,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or expired token"
  }
}
```

### 400 Bad Request
```json
{
  "status": "error",
  "data": null,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Missing required field: symbol"
  }
}
```

### 500 Server Error
```json
{
  "status": "error",
  "data": null,
  "error": {
    "code": "SERVER_ERROR",
    "message": "Internal server error"
  }
}
```

---

## HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | User not authorized for action |
| 404 | Not Found | Resource not found |
| 500 | Server Error | Internal error |

---

## Implementation Notes

1. **All endpoints must return 200 for successful requests** (with status: success)
2. **Error responses use appropriate HTTP status codes**
3. **Timestamps are ISO 8601 format (UTC)**
4. **All numbers are rounded to 2 decimal places**
5. **All endpoints require Authorization header with Bearer token** (except login endpoints)
