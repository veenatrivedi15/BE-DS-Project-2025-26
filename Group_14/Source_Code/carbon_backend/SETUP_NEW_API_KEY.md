# ✅ Setting Up Your New API Key

## 🎯 Your Configuration (Perfect!)

You've set up:
- ✅ Name: `carboncredits`
- ✅ Application restrictions: **Websites** ✓
- ✅ Website restrictions:
  - `http://127.0.0.1:8000/*` ✓
  - `http://localhost:8000/*` ✓
  - `https://carbon-credits.onrender.com/*` ✓
- ✅ API restrictions: **Don't restrict key** ✓

**Your new API key:** `AIzaSyBlhD0nAGUFMvmK5LsA2Na_fITiEjlWzQU`

---

## 📋 Next Steps

### **Step 1: Create the Key**
1. Click the blue **"Create"** button at the bottom
2. Wait for the key to be created
3. **Copy the API key** (it will be shown: `AIzaSyBlhD0nAGUFMvmK5LsA2Na_fITiEjlWzQU`)

### **Step 2: Set the API Key in Your Project**

**Option A: Environment Variable (Recommended)**
```powershell
# Windows PowerShell
$env:GOOGLE_MAPS_API_KEY="AIzaSyBlhD0nAGUFMvmK5LsA2Na_fITiEjlWzQU"
```

**Option B: .env File**
Create or edit `.env` file in `carbon_backend/` folder:
```
GOOGLE_MAPS_API_KEY=AIzaSyBlhD0nAGUFMvmK5LsA2Na_fITiEjlWzQU
```

### **Step 3: Restart Django Server**
1. Stop your Django server (Ctrl+C)
2. Start it again:
   ```bash
   python manage.py runserver
   ```

### **Step 4: Test**
1. Go to your trip log page
2. Clear browser cache: `Ctrl + Shift + Delete`
3. Refresh the page
4. ✅ Map should work!

---

## 🔒 Security Note

**Important:** Since you selected "Don't restrict key" for API restrictions, make sure to:

1. **Never commit this key to Git**
2. **Keep it in environment variables only**
3. **Consider restricting APIs later** (for production):
   - Go back to the API key settings
   - Select "Restrict key"
   - Choose only:
     - Maps JavaScript API
     - Places API
     - Geocoding API (if using)
     - Directions API (if using)

---

## ✅ You're All Set!

Your configuration is perfect for development. The map should work now!


