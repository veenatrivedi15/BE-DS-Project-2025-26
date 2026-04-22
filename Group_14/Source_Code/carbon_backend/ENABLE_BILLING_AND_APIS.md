# 🔧 Enable Billing and Directions API

## ❌ Current Errors

1. **BillingNotEnabledMapError** - Billing is not enabled
2. **Directions API REQUEST_DENIED** - Directions API is not enabled

## ✅ Fix Both Issues

### **Step 1: Enable Billing**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project ("Carbon Credits")
3. Click on **"Billing"** in the left menu (or search for it)
4. Click **"Link a billing account"**
5. Follow the prompts to:
   - Create a billing account (if you don't have one)
   - Add a payment method
   - Link it to your project

**Note:** Google gives $200 free credit per month, so you likely won't be charged for development usage.

---

### **Step 2: Enable Required APIs**

1. Go to **"APIs & Services"** → **"Library"** (in left menu)
2. Search for and enable these APIs:

   **Required:**
   - ✅ **Maps JavaScript API** (should already be enabled)
   - ✅ **Places API** (should already be enabled)
   - ✅ **Directions API** ← **ENABLE THIS ONE**
   - ✅ **Geocoding API** (optional but recommended)

3. For each API:
   - Click on it
   - Click the blue **"ENABLE"** button
   - Wait for confirmation

---

### **Step 3: Verify**

1. Go to **"APIs & Services"** → **"Enabled APIs"**
2. You should see:
   - Maps JavaScript API ✅
   - Places API ✅
   - Directions API ✅
   - Geocoding API ✅ (if enabled)

---

### **Step 4: Test**

1. Wait 1-2 minutes for changes to propagate
2. Clear browser cache: `Ctrl + Shift + Delete`
3. Refresh your trip log page
4. ✅ Map should work with route calculation!

---

## 🎯 Quick Checklist

- [ ] Billing account created and linked
- [ ] Maps JavaScript API enabled
- [ ] Places API enabled
- [ ] **Directions API enabled** ← Most important!
- [ ] Geocoding API enabled (optional)
- [ ] Waited 1-2 minutes
- [ ] Cleared browser cache
- [ ] Refreshed page

---

## 💡 What Happens After

Once billing and Directions API are enabled:
- ✅ Map will load without errors
- ✅ Route calculation will work
- ✅ Distance will be calculated accurately
- ✅ Directions will be displayed on map
- ✅ Location search will work perfectly

---

**The code now has a fallback that calculates straight-line distance if Directions API is unavailable, but enabling it will give you full route functionality!**


