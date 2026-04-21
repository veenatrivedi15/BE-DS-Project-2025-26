# Google Maps API Setup Guide

## 🔑 Required APIs

Make sure these APIs are **enabled** in your Google Cloud Console:

1. **Maps JavaScript API** (Required)
2. **Places API** (Required for search)
3. **Geocoding API** (Optional, for address conversion)
4. **Directions API** (Optional, for route calculation)

## 📝 Setup Steps

### 1. Get Your API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the required APIs (listed above)
4. Go to "Credentials" → "Create Credentials" → "API Key"
5. Copy your API key

### 2. Configure API Key Restrictions (Recommended)

**Application restrictions:**
- HTTP referrers (web sites)
- Add your domain: `http://localhost:8000/*`
- Add your domain: `http://127.0.0.1:8000/*`
- Add production domain when ready

**API restrictions:**
- Restrict key to only the APIs you need:
  - Maps JavaScript API
  - Places API
  - Geocoding API (if using)
  - Directions API (if using)

### 3. Set API Key in Django

**Option 1: Environment Variable (Recommended)**
```bash
# Windows PowerShell
$env:GOOGLE_MAPS_API_KEY="your-api-key-here"

# Windows CMD
set GOOGLE_MAPS_API_KEY=your-api-key-here

# Linux/Mac
export GOOGLE_MAPS_API_KEY="your-api-key-here"
```

**Option 2: .env File**
Create a `.env` file in `carbon_backend/`:
```
GOOGLE_MAPS_API_KEY=your-api-key-here
```

**Option 3: Direct in settings.py (Not Recommended for Production)**
```python
GOOGLE_MAPS_API_KEY = 'your-api-key-here'
```

### 4. Enable Billing (Required)

Google Maps requires a billing account to be enabled, even for free tier usage.

1. Go to Google Cloud Console
2. Navigate to "Billing"
3. Link a billing account
4. Free tier includes $200 credit per month

## 🐛 Troubleshooting

### Error: "This page didn't load Google Maps correctly"

**Possible causes:**

1. **API Key Not Set**
   - Check if `GOOGLE_MAPS_API_KEY` is set in environment
   - Verify it's passed to template context
   - Check browser console for errors

2. **API Not Enabled**
   - Go to Google Cloud Console
   - Check "APIs & Services" → "Enabled APIs"
   - Ensure "Maps JavaScript API" is enabled

3. **API Key Restrictions**
   - Check if HTTP referrer restrictions are blocking your domain
   - Add `http://localhost:8000/*` to allowed referrers
   - Temporarily remove restrictions to test

4. **Billing Not Enabled**
   - Google Maps requires billing to be enabled
   - Even free tier needs billing account linked

5. **Invalid API Key**
   - Verify the key is correct (no extra spaces)
   - Check if key was deleted/regenerated
   - Ensure key hasn't expired

### Check Browser Console

Open browser developer tools (F12) and check:
- Network tab: Is the Maps API script loading?
- Console tab: Any JavaScript errors?
- Look for specific error messages

### Test API Key

Test your API key directly:
```
https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY&libraries=places,geometry
```

If this returns an error, the issue is with the API key itself.

## ✅ Verification

After setup, verify:

1. **Check Settings:**
   ```python
   from django.conf import settings
   print(settings.GOOGLE_MAPS_API_KEY)  # Should print your key
   ```

2. **Check Template:**
   - View page source
   - Look for: `maps/api/js?key=YOUR_KEY`
   - Key should be visible (not the default test key)

3. **Check Browser Console:**
   - Should see: "Google Maps API loaded successfully"
   - No red errors about API key

## 🔒 Security Notes

- **Never commit API keys to Git**
- Use environment variables
- Add `.env` to `.gitignore`
- Restrict API key to specific domains
- Monitor API usage in Google Cloud Console

## 📚 Resources

- [Google Maps JavaScript API Docs](https://developers.google.com/maps/documentation/javascript)
- [API Key Best Practices](https://developers.google.com/maps/api-security-best-practices)
- [Billing Information](https://developers.google.com/maps/billing-and-pricing/pricing)


