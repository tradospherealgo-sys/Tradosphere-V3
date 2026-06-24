# 🚀 RAILWAY DEPLOYMENT GUIDE

## Quick Start: Railway.app Backend Deployment

**Status:** ✅ Code ready, pushed to GitHub  
**Next:** Deploy backend to Railway.app  

---

## 📋 OPTION 1: Deploy via Railway Dashboard (Easiest)

### Step 1: Connect GitHub Repository to Railway

1. Go to **https://railway.app/dashboard**
2. Click **"Create New Project"**
3. Select **"Deploy from GitHub"**
4. Authorize GitHub (if not already)
5. Select repository: `tradospherealgo-sys/Tradosphere-V3`
6. Select branch: `main`
7. Click **"Deploy"**

### Step 2: Configure Environment Variables

In Railway Dashboard:
1. Go to your project
2. Click **"Variables"** tab
3. Add all variables from `.env.development`:

```
FLASK_ENV=production
JWT_SECRET=your_secure_jwt_secret_here
DATABASE_URL=postgresql://user:password@host:port/dbname
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
ANGEL_ONE_CLIENT_CODE=M625536
ANGEL_ONE_PIN=your_pin
ANGEL_ONE_TOTP_SECRET=your_totp_secret
SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
REDIS_URL=redis://your_redis_url
```

### Step 3: Deploy

1. Railway will automatically detect:
   - `Procfile` for startup command
   - `runtime.txt` for Python version
   - `config/requirements.txt` for dependencies

2. It will:
   - Install dependencies
   - Run: `PORT=5000 python backend/tradosphere_saas_server_v3_1.py`
   - Start server on assigned port

3. Monitor deployment:
   - Watch logs in Railway dashboard
   - Check for any errors
   - Deployment takes ~3-5 minutes

### Step 4: Verify Deployment

Once deployment is complete:

```bash
# Get your Railway URL from dashboard
RAILWAY_URL="https://your-app.up.railway.app"

# Test health endpoint
curl $RAILWAY_URL/api/health
# Expected: {"status":"healthy","service":"Tradosphere SaaS v3.1"}

# Test status endpoint
curl $RAILWAY_URL/api/status
# Expected: Service info in JSON

# Test user signup
curl -X POST $RAILWAY_URL/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@railway.com","password":"Test@2024"}'
```

---

## 📋 OPTION 2: Deploy via Railway CLI

### Step 1: Install Railway CLI

```bash
# Using npm
npm install -g @railway/cli

# Or using Homebrew (macOS)
brew install railway
```

### Step 2: Login to Railway

```bash
railway login
# Opens browser to authenticate
```

### Step 3: Initialize Project

From project root:
```bash
cd /Users/anshhdodia/Desktop/tradosphere_v3.1
railway init

# Select: Create a new project
# Project name: tradosphere-v3
# Environment: production
```

### Step 4: Add Services

```bash
# Add PostgreSQL database
railway add
# Select: PostgreSQL

# This creates DATABASE_URL automatically
```

### Step 5: Set Environment Variables

```bash
railway variables set FLASK_ENV=production
railway variables set JWT_SECRET=your_secure_jwt_secret_here
railway variables set ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
railway variables set ANGEL_ONE_CLIENT_CODE=M625536
railway variables set ANGEL_ONE_PIN=your_pin
railway variables set ANGEL_ONE_TOTP_SECRET=your_totp_secret
railway variables set SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
```

### Step 6: Deploy

```bash
railway up
# Builds and deploys to Railway
# Monitoring deployment in real-time
```

### Step 7: Get Public URL

```bash
railway open
# Opens your deployed app in browser

# Or view URL:
railway status
```

---

## 🗄️ DATABASE SETUP FOR PRODUCTION

### Option A: Use Railway's PostgreSQL (Recommended)

Railway will automatically create `DATABASE_URL`:
```
postgresql://user:password@host:5432/dbname
```

The first time your app runs, it will initialize tables automatically via SQLAlchemy.

### Option B: Use External PostgreSQL

1. Get your PostgreSQL connection string
2. Set in Railway: `railway variables set DATABASE_URL=postgresql://...`

### Option C: Keep SQLite (Not Recommended for Production)

Current setup uses SQLite. For production, PostgreSQL is recommended because:
- Better for concurrent connections
- Easier backup/restore
- Better performance
- Horizontal scaling

---

## 🔍 POST-DEPLOYMENT VERIFICATION

### 1. Health Check
```bash
curl https://your-railway-url/api/health
```
Expected response:
```json
{
  "service": "Tradosphere SaaS v3.1",
  "status": "healthy",
  "timestamp": "2026-06-24T15:07:29Z"
}
```

### 2. User Authentication
```bash
# Signup
curl -X POST https://your-railway-url/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "prodtest@railway.com",
    "password": "ProdTest@2024"
  }'

# Login
curl -X POST https://your-railway-url/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "prodtest@railway.com",
    "password": "ProdTest@2024"
  }'

# You should receive JWT token
```

### 3. Market Data
```bash
# Using JWT token from login
TOKEN="your_jwt_token_here"

curl https://your-railway-url/api/market/live \
  -H "Authorization: Bearer $TOKEN"

# Should return live market data
```

### 4. Signal Generation
```bash
curl -X POST https://your-railway-url/api/signals \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NIFTY",
    "price": 24000,
    "change_percent": 2.5
  }'

# Should return trading signal with confidence score
```

### 5. Error Handling
```bash
# Test 404 error
curl https://your-railway-url/api/nonexistent
# Expected: 404 with proper error message

# Test 401 error (no auth)
curl https://your-railway-url/api/signals
# Expected: 401 with auth error
```

---

## 📊 MONITORING & LOGS

### View Logs in Railway Dashboard

1. Go to your Railway project
2. Click **"Logs"** tab
3. Filter by:
   - Deployment logs
   - Application logs
   - Error logs

### Real-Time Log Monitoring via CLI

```bash
railway logs -f
# Streams logs in real-time
```

### Error Tracking with Sentry

1. Configure `SENTRY_DSN` environment variable
2. Errors will be tracked at: https://sentry.io
3. Set up alerts for critical errors

---

## 🔄 ROLLBACK PROCEDURE

If issues occur:

### Via Railway Dashboard

1. Go to **Deployments** tab
2. Find previous successful deployment
3. Click **"Redeploy"**
4. Confirms with you, then rolls back

### Via Railway CLI

```bash
railway rollback
# Lists recent deployments
# Select the one to rollback to
```

---

## 📈 SCALING & PERFORMANCE

### Monitor Resource Usage

In Railway Dashboard:
- CPU usage
- Memory usage
- Network I/O
- Disk space

### Increase Resources

For higher load:
1. Upgrade plan in Railway
2. Increase RAM allocation
3. Enable auto-scaling

### Optimize Performance

- Enable Redis caching (Tier 2)
- Implement rate limiting (Tier 2)
- Use CDN for static assets (Vercel frontend)
- Database indexing

---

## ❌ TROUBLESHOOTING

### Application Won't Start

**Check logs:**
```bash
railway logs
```

**Common issues:**
- Missing environment variables → Add to Railway dashboard
- Dependency conflict → Check requirements.txt
- Import error → Check Python path

**Fix:**
```bash
# Update environment variables
railway variables set VARIABLE_NAME=value

# Redeploy
railway up
```

### Database Connection Failed

**Error:** `postgresql://...` connection error

**Fix:**
1. Verify DATABASE_URL is set correctly
2. Check PostgreSQL service is running
3. Verify credentials are correct
4. Wait 30 seconds for database to be ready

### Market Data Not Showing

**Check:**
1. Angel One credentials in env variables
2. Internet connectivity
3. API rate limits

```bash
railway logs | grep "Angel One"
# Check for authentication errors
```

### Errors Not Appearing in Logs

**Enable debug mode:**
```bash
railway variables set FLASK_ENV=development
railway up
# See more verbose output
```

---

## 🔐 SECURITY CHECKLIST

- [ ] Verify no secrets in GitHub (use environment variables)
- [ ] JWT_SECRET is strong (minimum 32 characters)
- [ ] SENTRY_DSN is configured for error tracking
- [ ] HTTPS enabled (Railway provides SSL by default)
- [ ] CORS settings configured for frontend domain
- [ ] API keys not exposed in logs
- [ ] Database credentials in environment variables only

---

## 📝 ENVIRONMENT VARIABLES REFERENCE

```bash
# Flask Configuration
FLASK_ENV=production                              # production or development
DEBUG=False                                        # Disable debug mode

# Security
JWT_SECRET=your_super_secret_key_32_chars_min    # Must be strong
SECRET_KEY=your_secret_key                        # Flask secret

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db # PostgreSQL for prod

# Angel One Integration
ANGEL_ONE_CLIENT_CODE=M625536                     # Broker client code
ANGEL_ONE_PIN=3958                                # Broker PIN
ANGEL_ONE_TOTP_SECRET=xxxx                        # TOTP secret for 2FA

# Claude AI (Optional)
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx            # Claude API key

# Error Tracking
SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/ # Sentry error tracking

# Caching (Tier 2)
REDIS_URL=redis://user:pass@host:6379            # Redis cache URL
```

---

## ✅ DEPLOYMENT CHECKLIST

- [ ] Code pushed to GitHub
- [ ] Created Railway project
- [ ] Connected GitHub repository
- [ ] Added all environment variables
- [ ] Verified Procfile exists
- [ ] Verified requirements.txt updated
- [ ] Deployment successful (green status)
- [ ] Health check passing
- [ ] User login working
- [ ] Market data showing
- [ ] Errors logged to Sentry
- [ ] Monitoring dashboard set up

---

## 🎉 NEXT: VERCEL FRONTEND DEPLOYMENT

After Railway backend is stable:
1. Prepare frontend code (separate repository)
2. Deploy to Vercel
3. Connect frontend to production API
4. Run end-to-end tests

See **VERCEL_DEPLOYMENT_GUIDE.md** for frontend deployment.

---

**Status:** Backend ready for Railway deployment ✅  
**Confidence:** 100% - All Tier 1 features verified  
**Next Step:** Deploy to Railway → Test → Deploy to Vercel
