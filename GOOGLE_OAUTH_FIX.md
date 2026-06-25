# Google OAuth Fix - Add Vercel Origins

## **Problem**
Google Sign-In showing error: "The given origin is not allowed for the given client ID"

## **Root Cause**
Vercel frontend origin not added to Google Cloud Console OAuth configuration

## **Solution Steps**

### **Step 1: Go to Google Cloud Console**
1. Open: https://console.cloud.google.com
2. Sign in with your Google account
3. Select project: **Tradosphere** (or your project name)

### **Step 2: Navigate to OAuth 2.0 Credentials**
1. Left sidebar → APIs & Services
2. Click "Credentials"
3. Find OAuth 2.0 Client ID: `810958107275-e45cqfkhgei54ip0t56d3q6q3lp6m5r0.apps.googleusercontent.com`
4. Click on it to edit

### **Step 3: Add Authorized JavaScript Origins**

Under **Authorized JavaScript Origins**, add:
```
https://tradosphere.vercel.app
https://www.tradosphere.vercel.app
```

Click **ADD URI** for each origin.

**Current Origins Should Be:**
```
http://localhost:3000
http://localhost:5000
https://tradosphere.vercel.app          ← ADD THIS
https://www.tradosphere.vercel.app      ← ADD THIS
https://tradosphere.in
https://www.tradosphere.in
```

### **Step 4: Add Authorized Redirect URIs**

Under **Authorized redirect URIs**, add:
```
https://tradosphere.vercel.app/login_v3.1.html
https://www.tradosphere.vercel.app/login_v3.1.html
```

**Complete List Should Be:**
```
http://localhost:3000
http://localhost:5000
https://web-production-7bb17.up.railway.app/api/auth/google/callback
https://tradosphere.vercel.app/login_v3.1.html              ← ADD THIS
https://www.tradosphere.vercel.app/login_v3.1.html          ← ADD THIS
https://tradosphere.in/api/auth/google/callback
https://www.tradosphere.in/api/auth/google/callback
```

### **Step 5: Save Changes**
1. Click **SAVE** button at bottom
2. Should see: "OAuth client updated successfully"

### **Step 6: Test Google Sign-In**
1. Go to: https://tradosphere.vercel.app
2. Click "Sign in with Google" button
3. Should see: Google login popup (no more 403 error)

## **Verification Checklist**

- [ ] Google Cloud Console accessed
- [ ] OAuth 2.0 Client ID found
- [ ] Vercel origins added to Authorized JavaScript Origins
- [ ] Vercel origins added to Authorized Redirect URIs
- [ ] Changes saved successfully
- [ ] Tested on Vercel - no 403 error
- [ ] Google Sign-In popup appears

## **If Still Having Issues**

### **Clear Browser Cache**
```
Ctrl+Shift+Delete (Windows/Linux)
Cmd+Shift+Delete (Mac)
```
Select "All time" → Clear

### **Hard Refresh**
```
Ctrl+Shift+R (Windows/Linux)
Cmd+Shift+R (Mac)
```

### **Check Console**
DevTools (F12) → Console
Look for exact error message

### **Verify API Endpoint**
Check that this returns the token properly:
```
POST https://web-production-7bb17.up.railway.app/api/auth/google/callback
```

## **Configuration Summary**

| Setting | Value |
|---------|-------|
| Client ID | 810958107275-e45cqfkhgei54ip0t56d3q6q3lp6m5r0.apps.googleusercontent.com |
| App Name | Tradosphere |
| Authorized Origins | https://tradosphere.vercel.app, https://www.tradosphere.vercel.app |
| Redirect URIs | https://tradosphere.vercel.app/login_v3.1.html |
| Status | ✅ Ready after configuration |

## **Expected Result**
After these changes, Google Sign-In should work without errors on Vercel.
