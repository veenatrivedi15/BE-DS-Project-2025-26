# Debugging Google Maps Error - Step by Step Guide

## 🔍 Current Error
"Sorry! Something went wrong. This page didn't load Google Maps correctly."

## 📋 Step-by-Step Debugging

### **Step 1: Check API Key is Set**

Open your browser console (F12) and look for:
```
Google Maps API Key configured: AIzaSy...
```

**If you see "API key not configured":**
1. Set the environment variable:
   ```powershell
   $env:GOOGLE_MAPS_API_KEY="your-actual-api-key"
   ```
2. Restart Django server
3. Refresh the page

### **Step 2: Check Browser Console**

Open Developer Tools (F12) → Console tab

**Look for these messages:**
- ✅ "initMap called - Google Maps API callback triggered"
- ✅ "Google Maps API is available"
- ✅ "Map created successfully"

**Or errors like:**
- ❌ "Google Maps API not loaded"
- ❌ "Failed to load Google Maps API script"
- ❌ "gm_authFailure" (authentication error)

### **Step 3: Check Network Tab**

1. Open Developer Tools (F12) → Network tab
2. Refresh the page
3. Look for: `maps/api/js?key=...`

**If the request fails:**
- Red status code (400, 403, etc.)
- Check the error message in the response

**Common errors:**
- **403 Forbidden**: API key invalid or restrictions blocking
- **400 Bad Request**: Invalid API key format
- **Network error**: Connection issue

### **Step 4: Test API Key Directly**

Open this URL in your browser (replace YOUR_KEY):
```
https://maps.googleapis.com/maps/api/js?key=YOUR_KEY&libraries=places,geometry
```

**If you see:**
- JavaScript code → API key is valid ✅
- Error message → API key is invalid ❌

### **Step 5: Check Google Cloud Console**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Go to "APIs & Services" → "Enabled APIs"
4. **Check these are enabled:**
   - ✅ Maps JavaScript API
   - ✅ Places API
   - ✅ Geocoding API (optional)
   - ✅ Directions API (optional)

### **Step 6: Check API Key Restrictions**

1. Go to "APIs & Services" → "Credentials"
2. Click on your API key
3. Check "Application restrictions"

**If "HTTP referrers" is set:**
- Add: `http://localhost:8000/*`
- Add: `http://127.0.0.1:8000/*`
- Add your production domain

**If "IP addresses" is set:**
- This won't work for localhost
- Switch to "HTTP referrers" instead

### **Step 7: Check Billing**

1. Go to "Billing" in Google Cloud Console
2. **Billing MUST be enabled** (even for free tier)
3. Link a billing account if not already linked

### **Step 8: Common Issues & Solutions**

#### **Issue: "gm_authFailure" in console**
**Solution:** API key is invalid or restricted
- Verify API key is correct
- Check restrictions allow localhost
- Ensure APIs are enabled

#### **Issue: Script loads but map doesn't appear**
**Solution:** Check console for JavaScript errors
- Look for errors after "initMap called"
- Check if map element exists
- Verify no JavaScript conflicts

#### **Issue: "This page didn't load Google Maps correctly"**
**Solution:** Usually API key or billing issue
- Verify API key in settings
- Check billing is enabled
- Ensure Maps JavaScript API is enabled

## 🔧 Quick Fixes

### **Fix 1: Clear Browser Cache**
1. Press Ctrl+Shift+Delete
2. Clear cached images and files
3. Refresh page

### **Fix 2: Test in Incognito Mode**
1. Open incognito/private window
2. Navigate to trip log page
3. Check if map loads

### **Fix 3: Check Django Settings**
```python
# In carbon_backend/settings.py or .env
GOOGLE_MAPS_API_KEY = 'your-actual-key-here'
```

### **Fix 4: Verify Template Context**
The view should pass `google_maps_api_key` to template:
```python
context = {
    'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
}
```

## 📝 What to Check in Console

**Good signs:**
```
✅ initMap called - Google Maps API callback triggered
✅ Google Maps API is available
✅ Google Maps version: 3.xx
✅ Map created successfully
```

**Bad signs:**
```
❌ Google Maps API not loaded
❌ Failed to load Google Maps API script
❌ gm_authFailure
❌ Map element not found
```

## 🆘 Still Not Working?

1. **Share the console output** (screenshot or copy/paste)
2. **Check the Network tab** for failed requests
3. **Verify API key** in Google Cloud Console
4. **Test API key** directly in browser URL

---

**The code now has extensive logging. Check the browser console for specific error messages!**


