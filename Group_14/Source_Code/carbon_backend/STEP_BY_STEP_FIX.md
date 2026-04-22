# 📋 Step-by-Step: Fix API Key Restrictions

## 🎯 You're Currently On: APIs & Services Page

### **Step 1: Go to Credentials**
1. Look at the **left navigation menu** (on the left side of your screen)
2. You should see "APIs & Services" at the top
3. Click on **"Credentials"** (it has a key 🔑 icon)
   - It's the third item in the list
   - Right below "Library"

### **Step 2: Find Your API Key**
1. You'll see a list of API keys
2. Look for the one that starts with: `AIzaSyD-9t...`
3. **Click on the API key name** (not the edit icon, click the name itself)

### **Step 3: Update Application Restrictions**
1. You'll see a page with API key details
2. Scroll down to find **"Application restrictions"** section
3. You'll see options like:
   - None
   - IP addresses
   - HTTP referrers (web sites) ← **SELECT THIS ONE**
   - Android apps
   - iOS apps

4. **Select "HTTP referrers (web sites)"**

### **Step 4: Add Your Localhost URLs**
1. Under "Website restrictions", you'll see a list (might be empty)
2. Click **"ADD AN ITEM"** button
3. In the text box that appears, type:
   ```
   http://localhost:8000/*
   ```
4. Click **"ADD AN ITEM"** again
5. In the new text box, type:
   ```
   http://127.0.0.1:8000/*
   ```

### **Step 5: Save**
1. Scroll to the bottom of the page
2. Click the blue **"SAVE"** button
3. Wait for the confirmation message

### **Step 6: Wait and Test**
1. **Wait 1-2 minutes** for changes to take effect
2. Go back to your trip log page
3. **Clear browser cache**: Press `Ctrl + Shift + Delete`
   - Select "Cached images and files"
   - Click "Clear data"
4. **Refresh the page** (F5 or Ctrl+R)
5. ✅ Map should now work!

---

## 🆘 If You Can't Find Credentials

**Alternative Path:**
1. In the search bar at the top (where you typed "maps")
2. Type: **"credentials"**
3. Click on "Credentials" from the search results
4. Then follow Step 2 above

---

## 📸 What You Should See

**After Step 3, your screen should show:**
- "Application restrictions" section
- Radio button selected: "HTTP referrers (web sites)"
- A list box with website restrictions
- "ADD AN ITEM" button

**After Step 4, you should have:**
- `http://localhost:8000/*` in the list
- `http://127.0.0.1:8000/*` in the list

---

## ✅ Quick Checklist

- [ ] Clicked "Credentials" in left menu
- [ ] Found and clicked on API key (AIzaSyD-9t...)
- [ ] Selected "HTTP referrers (web sites)"
- [ ] Added `http://localhost:8000/*`
- [ ] Added `http://127.0.0.1:8000/*`
- [ ] Clicked "SAVE"
- [ ] Waited 1-2 minutes
- [ ] Cleared browser cache
- [ ] Refreshed trip log page

---

**You're almost there! Just follow these steps and your map will work! 🎉**


