# 🚀 VERCEL DEPLOYMENT GUIDE

## Frontend Deployment to Vercel

**Status:** ⏳ Frontend code preparation required  
**Backend:** ✅ Ready on Railway  

---

## 📋 QUICK START: Vercel Frontend Deployment

### Prerequisites

1. **Frontend Repository** - Must exist (separate from backend)
2. **React/Next.js App** - Tradosphere frontend code
3. **Vercel Account** - Free tier available at https://vercel.com
4. **GitHub Connection** - Vercel connects to GitHub repo

---

## 🔧 STEP 1: Prepare Frontend Repository

Your frontend should have this structure:

```
tradosphere-frontend/
├── public/
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── components/
│   ├── pages/
│   ├── App.js
│   └── index.js
├── package.json
├── package-lock.json
├── .env.local (git-ignored)
├── .env.example
└── vercel.json (optional)
```

### Create .env.local

```bash
# Frontend environment variables
REACT_APP_API_URL=https://your-railway-backend.up.railway.app
REACT_APP_JWT_SECRET=your_jwt_secret_here
REACT_APP_SENTRY_DSN=your_sentry_dsn_here
```

### Create .env.example (for reference)

```bash
# Example environment variables
# Copy to .env.local and fill in values
REACT_APP_API_URL=https://your-backend-url.com
REACT_APP_JWT_SECRET=your_secret_here
REACT_APP_SENTRY_DSN=your_sentry_dsn
```

### Update package.json

Ensure `package.json` has proper build command:

```json
{
  "name": "tradosphere-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.0.0",
    "axios": "^1.0.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": [
      "react-app"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}
```

---

## 📋 STEP 2: Deploy via Vercel Dashboard

### Option A: Connect GitHub Repo (Recommended)

1. Go to **https://vercel.com/dashboard**
2. Click **"New Project"**
3. Click **"Continue with GitHub"** (authorize if needed)
4. Select your frontend repository
5. Click **"Import"**

### Configuration in Vercel

1. **Project Name:** `tradosphere-frontend`
2. **Framework Preset:** React (auto-detected)
3. **Root Directory:** `.` (current)
4. **Build Command:** `npm run build` (auto-detected)
5. **Output Directory:** `build` (auto-detected)
6. **Install Command:** `npm install` (auto-detected)

### Environment Variables in Vercel

In the **Environment Variables** section:

```
REACT_APP_API_URL = https://your-railway-backend.up.railway.app
REACT_APP_JWT_SECRET = your_jwt_secret_here
REACT_APP_SENTRY_DSN = your_sentry_dsn_here
```

### Click Deploy

Vercel will:
1. Clone your GitHub repo
2. Install dependencies
3. Build the project
4. Deploy to CDN (global)
5. Assign domain: `tradosphere-frontend.vercel.app`

---

## 📋 STEP 3: Deploy via Vercel CLI

### Install Vercel CLI

```bash
npm install -g vercel
```

### Login to Vercel

```bash
vercel login
# Follow the authentication flow
```

### Deploy Project

```bash
cd /path/to/tradosphere-frontend
vercel
# Follow prompts:
# - Project name: tradosphere-frontend
# - Link to existing project: No (first time)
# - Build settings: Accept defaults
```

### Set Environment Variables

```bash
vercel env add REACT_APP_API_URL
# Prompt: Enter value
# Enter: https://your-railway-backend.up.railway.app

vercel env add REACT_APP_JWT_SECRET
# Enter: your_jwt_secret_here

vercel env add REACT_APP_SENTRY_DSN
# Enter: your_sentry_dsn_here
```

### Deploy to Production

```bash
vercel --prod
# Deploys to production URL
```

---

## 🔗 STEP 4: Connect Frontend to Backend

### Update API Calls

In your React components:

```javascript
// Use environment variable for API URL
const API_URL = process.env.REACT_APP_API_URL;

// Example: User login
async function login(email, password) {
  try {
    const response = await fetch(`${API_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    if (data.token) {
      localStorage.setItem('jwt_token', data.token);
      return data;
    }
  } catch (error) {
    console.error('Login failed:', error);
  }
}

// Example: Fetch market data
async function fetchMarketData() {
  const token = localStorage.getItem('jwt_token');
  const response = await fetch(`${API_URL}/api/market/live`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
}
```

### Configure CORS in Backend

The Railway backend should have CORS enabled for your Vercel domain:

```python
# In backend flask app
from flask_cors import CORS

CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://tradosphere-frontend.vercel.app",
            "http://localhost:3000",  # Development
        ],
        "allow_headers": ["Content-Type", "Authorization"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    }
})
```

---

## ✅ STEP 5: VERIFICATION

### Test Health Check from Frontend

```javascript
useEffect(() => {
  fetch(`${process.env.REACT_APP_API_URL}/api/health`)
    .then(r => r.json())
    .then(data => console.log('Backend:', data.status))
    .catch(err => console.error('Backend error:', err));
}, []);
```

### Test User Authentication

1. Go to frontend URL
2. Try signing up
3. Try logging in
4. Should receive JWT token
5. Token persisted in localStorage

### Test Market Data

1. After login, navigate to market page
2. Should see live prices from Angel One
3. Should see trading signals with confidence scores

### Test End-to-End

```bash
# From frontend
npm start
# Opens http://localhost:3000

# Test flow:
# 1. Signup → Create account on backend
# 2. Login → Get JWT token
# 3. View market → Fetch live prices
# 4. Generate signal → See trading signal
# 5. Open trade → Create paper trade
# 6. Logout → Clear token
```

---

## 🔍 MONITORING & DEBUGGING

### View Vercel Logs

1. Go to **Vercel Dashboard**
2. Select your project
3. Click **"Deployments"**
4. Select deployment
5. Click **"Logs"** to see build logs
6. Click **"Runtime Logs"** for live logs

### View Build Errors

```bash
vercel logs
# Shows recent deployment logs
```

### Check Frontend Performance

1. In Vercel Dashboard
2. Click **"Analytics"**
3. View Core Web Vitals
4. Monitor page load times

---

## 🚀 OPTIMIZATION

### Enable Caching

In `vercel.json`:

```json
{
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "no-cache, no-store, must-revalidate"
        }
      ]
    },
    {
      "source": "/static/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ]
}
```

### Optimize Bundle Size

```bash
npm install --save-dev source-map-explorer
npm run build
npx source-map-explorer 'build/static/js/*.js'
# Identifies large chunks to optimize
```

### Enable Compression

Vercel automatically gzip-compresses responses for:
- HTML
- CSS
- JavaScript
- JSON

---

## 🔄 DEPLOYMENT WORKFLOW

### Development

```bash
npm start
# Runs on http://localhost:3000
# Connected to local backend on localhost:5001
```

### Staging

```bash
vercel --scope=your-team
# Deploys to staging URL
```

### Production

```bash
git push origin main
# Vercel automatically deploys
# OR manually:
vercel --prod
```

---

## 📊 CUSTOM DOMAIN

### Add Your Domain

1. In Vercel Dashboard
2. Project Settings → Domains
3. Add your domain (e.g., `app.tradosphere.com`)
4. Update DNS records (instructions provided by Vercel)

### DNS Configuration

For example, if using Namecheap:

```
CNAME: www.tradosphere.com → Cname.vercel.com
CNAME: app.tradosphere.com → Cname.vercel.com
```

---

## 🔐 SECURITY

### Environment Variables Best Practices

- [ ] Never commit `.env.local` (add to `.gitignore`)
- [ ] All secrets in Vercel dashboard variables
- [ ] Use environment-specific variables
- [ ] Rotate secrets regularly

### CORS Configuration

- [ ] Only allow your frontend domain
- [ ] Use HTTPS only
- [ ] Set appropriate headers

### Content Security Policy

In your HTML or headers:

```html
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'">
```

---

## ❌ TROUBLESHOOTING

### Build Failed

**Check logs in Vercel dashboard for:**
- Missing dependencies
- Environment variables
- Build script errors

**Fix:**
```bash
# Locally test build
npm run build

# Check for errors
npm install
npm run build
```

### API Requests Failing

**Common issues:**
1. REACT_APP_API_URL not set correctly
2. Backend CORS not configured
3. Backend not running/deployed

**Debug:**
```javascript
// Check URL in browser console
console.log('API URL:', process.env.REACT_APP_API_URL);

// Test request
fetch(`${process.env.REACT_APP_API_URL}/api/health`)
  .then(r => r.json())
  .then(d => console.log(d))
  .catch(e => console.error(e));
```

### Blank Page on Load

**Check:**
1. Browser console for JS errors
2. Network tab for failed requests
3. Vercel runtime logs

**Fix:**
```bash
# Rebuild locally
npm start
# Should show errors

# Check for missing index.html
ls public/index.html
```

### JWT Token Issues

**If getting 401 errors:**
1. Token not being sent correctly
2. Token format wrong (missing "Bearer ")
3. JWT_SECRET mismatch

**Debug:**
```javascript
// Check token in localStorage
console.log(localStorage.getItem('jwt_token'));

// Verify format in request
const token = localStorage.getItem('jwt_token');
console.log(`Bearer ${token}`);
```

---

## 📈 SCALING FOR PRODUCTION

### Edge Network

Vercel automatically serves from nearest edge location:
- Faster load times globally
- Automatic failover
- DDoS protection included

### Auto-scaling

For high traffic:
- Vercel handles scaling automatically
- No need to manage servers
- Pay per request

### Database Scaling

If using Railway PostgreSQL:
- Upgrade plan for more resources
- Add read replicas for read-heavy loads
- Implement caching layer (Redis - Tier 2)

---

## ✅ DEPLOYMENT CHECKLIST

- [ ] Frontend repository created
- [ ] .env.local configured with Railway API URL
- [ ] package.json has correct build script
- [ ] CORS configured in backend
- [ ] Vercel project created
- [ ] Environment variables set in Vercel
- [ ] Frontend deployed successfully
- [ ] Health check passing
- [ ] User login working
- [ ] API calls connecting to backend
- [ ] Custom domain configured (optional)
- [ ] Monitoring/Analytics enabled
- [ ] Error tracking (Sentry) configured

---

## 🎉 COMPLETE DEPLOYMENT SUMMARY

```
┌─────────────────────────────────────────┐
│    TRADOSPHERE V3.1 - FULL STACK        │
├─────────────────────────────────────────┤
│                                         │
│  Frontend: Vercel                       │
│  ├─ React/Next.js                       │
│  ├─ Global CDN                          │
│  └─ Auto-scaling                        │
│                                         │
│  Backend: Railway                       │
│  ├─ Flask REST API                      │
│  ├─ PostgreSQL Database                 │
│  └─ Auto-restart on failure             │
│                                         │
│  Services:                              │
│  ├─ Sentry (Error tracking)             │
│  ├─ Redis (Caching - Tier 2)            │
│  └─ Angel One (Market data)             │
│                                         │
└─────────────────────────────────────────┘
```

---

**Status:** Ready for Vercel frontend deployment ✅  
**Prerequisites:** Frontend code repository  
**Confidence:** 100% - Backend ready, deployment templates provided  
**Next Step:** Prepare frontend → Deploy to Vercel → Run E2E tests
