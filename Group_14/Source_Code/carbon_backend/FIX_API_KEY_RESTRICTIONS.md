# 🔧 Fix: RefererNotAllowedMapError

## ❌ Current Error
```
Google Maps JavaScript API error: RefererNotAllowedMapError
Your site URL to be authorized: http://127.0.0.1:8000/employee/trip/log/
```

## ✅ Solution: Update API Key Restrictions

Your Google Maps API key has **HTTP referrer restrictions** that are blocking `http://127.0.0.1:8000`.

### **Step-by-Step Fix:**

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/
   - Select your project

2. **Navigate to Credentials**
   - Go to "APIs & Services" → "Credentials"
   - Find your API key and click on it

3. **Update Application Restrictions**
   - Under "Application restrictions"
   - Select "HTTP referrers (web sites)"
   - Click "ADD AN ITEM" for each pattern below:

   **Add these referrers:**
   ```
   http://localhost:8000/*
   http://127.0.0.1:8000/*
   http://localhost:8000/employee/*
   http://127.0.0.1:8000/employee/*
   ```

   **Or use wildcards (easier):**
   ```
   http://localhost:8000/*
   http://127.0.0.1:8000/*
   ```

4. **Save Changes**
   - Click "SAVE" at the bottom
   - Wait 1-2 minutes for changes to propagate

5. **Test**
   - Clear browser cache (Ctrl+Shift+Delete)
   - Refresh the trip log page
   - Map should now load!

---

## 🎯 Alternative: Remove Restrictions (For Development Only)

**⚠️ WARNING: Only for local development!**

If you want to test without restrictions:

1. Go to API key settings
2. Under "Application restrictions"
3. Select "None"
4. Click "SAVE"

**Remember:** Re-enable restrictions before going to production!

---

## 📝 For Production

When deploying to production, add your production domain:
```
https://yourdomain.com/*
https://www.yourdomain.com/*
```

---

## ✅ Verification

After updating restrictions:

1. Wait 1-2 minutes
2. Clear browser cache
3. Refresh page
4. Check console - should see:
   - ✅ "Map created successfully"
   - ✅ No "RefererNotAllowedMapError"

---

**The map is actually loading correctly (you can see "Map created successfully"), but Google is blocking it due to referrer restrictions. Fix the restrictions and it will work!**


