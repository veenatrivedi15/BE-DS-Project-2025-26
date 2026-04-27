# 🗺️ Visual Guide: Fixing API Key Restrictions

## Current Screen: APIs & Services

You're on the right page! Now follow these steps:

---

## 📍 Step 1: Click "Credentials"

**Look at the LEFT SIDE of your screen**

You should see a menu that says:
```
APIs & Services
├── Enabled APIs & services  ← (currently selected)
├── Library
├── Credentials              ← CLICK THIS ONE! 🔑
├── OAuth consent screen
└── Page usage agreements
```

**Click on "Credentials"** (the one with the key icon 🔑)

---

## 📍 Step 2: Find Your API Key

After clicking Credentials, you'll see a page with:

**API keys** section at the top

Look for a key that starts with:
```
AIzaSyD-9tSrke72PouQMnMX-a7eZSW0jkFMBWY
```

**Click on the NAME of the API key** (not any icons, click the actual name)

---

## 📍 Step 3: Edit Restrictions

You'll now see a page titled something like:
**"Edit API key"** or **"API key details"**

Scroll down until you see:

### **Application restrictions**
```
○ None
○ IP addresses (web servers, cron jobs, etc.)
● HTTP referrers (web sites)  ← SELECT THIS ONE
○ Android apps
○ iOS apps
```

**Click the radio button next to "HTTP referrers (web sites)"**

---

## 📍 Step 4: Add Website Restrictions

Below the radio buttons, you'll see:

**Website restrictions**
```
┌─────────────────────────────────────┐
│ [Empty list or existing items]     │
└─────────────────────────────────────┘
[+ ADD AN ITEM]  ← Click this button
```

1. **Click "+ ADD AN ITEM"**
2. A text box will appear
3. Type: `http://localhost:8000/*`
4. **Click "+ ADD AN ITEM"** again
5. Type: `http://127.0.0.1:8000/*`

You should now see:
```
Website restrictions
┌─────────────────────────────────────┐
│ http://localhost:8000/*             │
│ http://127.0.0.1:8000/*             │
└─────────────────────────────────────┘
```

---

## 📍 Step 5: Save

Scroll to the **BOTTOM** of the page

You'll see buttons:
```
[Cancel]  [SAVE]  ← Click SAVE (blue button)
```

**Click "SAVE"**

You'll see a message like: "API key updated successfully"

---

## 📍 Step 6: Wait and Test

1. **Wait 1-2 minutes** (Google needs time to update)
2. Go back to your trip log page
3. **Clear cache**: `Ctrl + Shift + Delete` → Clear cached files
4. **Refresh**: Press `F5` or click refresh button
5. ✅ **Map should work!**

---

## 🆘 Troubleshooting

### Can't find "Credentials"?
- Use the search bar at the top
- Type: `credentials`
- Click the first result

### Don't see "HTTP referrers" option?
- Make sure you clicked on the API KEY itself (not just the list)
- You need to be in "Edit API key" mode

### Changes not working?
- Wait longer (up to 5 minutes)
- Make sure you clicked SAVE
- Check that both URLs are in the list
- Try removing restrictions temporarily (select "None") to test

---

**Follow these steps exactly and your map will work! 🚀**


